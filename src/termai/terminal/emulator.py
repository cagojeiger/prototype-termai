import fcntl
import os
import pty
import select
import signal
import struct
import subprocess
import termios
import threading
from collections.abc import Callable


class TerminalEmulator:
    """PTY-based terminal emulator for shell process management"""

    def __init__(self, shell: str = None):
        self.shell = shell or os.environ.get("SHELL", "/bin/bash")
        self.process: subprocess.Popen | None = None
        self.master_fd: int | None = None
        self.slave_fd: int | None = None

        self.cols = 80
        self.rows = 24

        self.output_thread: threading.Thread | None = None
        self.running = False

        self.on_output: Callable[[bytes], None] | None = None
        self.on_exit: Callable[[int], None] | None = None

        self._buffer = b""

    def start(self):
        """Start the terminal emulator with PTY"""
        if self.running:
            return

        try:
            self.master_fd, self.slave_fd = pty.openpty()

            self._set_terminal_size()

            self.process = subprocess.Popen(
                [self.shell],
                stdin=self.slave_fd,
                stdout=self.slave_fd,
                stderr=self.slave_fd,
                preexec_fn=os.setsid,
                cwd=os.getcwd(),
                env=os.environ.copy(),
            )

            os.close(self.slave_fd)
            self.slave_fd = None

            flags = fcntl.fcntl(self.master_fd, fcntl.F_GETFL)
            fcntl.fcntl(self.master_fd, fcntl.F_SETFL, flags | os.O_NONBLOCK)

            self.running = True
            self.output_thread = threading.Thread(
                target=self._read_output_loop, daemon=True
            )
            self.output_thread.start()

        except Exception as e:
            self._cleanup()
            raise RuntimeError(f"Failed to start terminal emulator: {e}") from e

    def stop(self):
        """Stop the terminal emulator and cleanup resources"""
        if not self.running:
            return

        self.running = False

        if self.process:
            try:
                os.killpg(os.getpgid(self.process.pid), signal.SIGTERM)

                try:
                    exit_code = self.process.wait(timeout=2.0)
                    if self.on_exit:
                        self.on_exit(exit_code)
                except subprocess.TimeoutExpired:
                    os.killpg(os.getpgid(self.process.pid), signal.SIGKILL)
                    exit_code = self.process.wait()
                    if self.on_exit:
                        self.on_exit(exit_code)

            except (ProcessLookupError, OSError):
                pass

        if self.output_thread and self.output_thread.is_alive():
            self.output_thread.join(timeout=1.0)

        self._cleanup()

    def write_text(self, text: str):
        """Write text to the terminal"""
        if not self.running or not self.master_fd:
            return

        try:
            data = text.encode("utf-8")
            os.write(self.master_fd, data)
        except (OSError, BrokenPipeError):
            pass

    def resize(self, cols: int, rows: int):
        """Resize the terminal"""
        self.cols = cols
        self.rows = rows

        if self.master_fd:
            self._set_terminal_size()

    def read_output(self, timeout: float = 0.1) -> bytes:
        """Read available output from terminal"""
        if not self.running or not self.master_fd:
            return b""

        try:
            ready, _, _ = select.select([self.master_fd], [], [], timeout)
            if ready:
                data = os.read(self.master_fd, 4096)
                return data
        except (OSError, ValueError):
            pass

        return b""

    def is_running(self) -> bool:
        """Check if terminal emulator is running"""
        return bool(self.running and self.process and self.process.poll() is None)

    def get_exit_code(self) -> int | None:
        """Get exit code of shell process"""
        if self.process:
            return self.process.poll()
        return None

    def _set_terminal_size(self):
        """Set terminal window size"""
        if not self.master_fd:
            return

        try:
            size = struct.pack("HHHH", self.rows, self.cols, 0, 0)
            fcntl.ioctl(self.master_fd, termios.TIOCSWINSZ, size)
        except (OSError, ValueError):
            pass

    def _read_output_loop(self):
        """Background thread for reading terminal output"""
        while self.running:
            try:
                ready, _, _ = select.select([self.master_fd], [], [], 0.1)

                if ready and self.master_fd:
                    try:
                        data = os.read(self.master_fd, 4096)
                        if data:
                            self._buffer += data
                            self._process_buffer()
                        else:
                            break
                    except (OSError, ValueError):
                        break

            except Exception:
                break

        if self._buffer and self.on_output:
            self.on_output(self._buffer)
            self._buffer = b""

    def _process_buffer(self):
        """Process buffered output data"""
        if not self._buffer:
            return

        if self.on_output:
            self.on_output(self._buffer)

        self._buffer = b""

    def _cleanup(self):
        """Clean up file descriptors and resources"""
        if self.master_fd:
            try:
                os.close(self.master_fd)
            except OSError:
                pass
            self.master_fd = None

        if self.slave_fd:
            try:
                os.close(self.slave_fd)
            except OSError:
                pass
            self.slave_fd = None

        self.process = None
        self.output_thread = None
