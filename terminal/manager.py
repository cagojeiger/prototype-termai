import os
import re
from typing import Callable, List, Optional

from .buffer import OutputBuffer
from .emulator import TerminalEmulator
from .history import CommandHistory


class TerminalManager:
    """터미널 기능 통합 관리"""

    def __init__(self):
        self.emulator = TerminalEmulator()
        self.buffer = OutputBuffer()
        self.history = CommandHistory()

        self.current_directory = os.getcwd()
        self.current_command = ""
        self.command_running = False

        self.prompt_patterns = [
            re.compile(r".*[$#]\s*$"),  # bash/sh
            re.compile(r".*[>]\s*$"),  # fish
            re.compile(r".*[%]\s*$"),  # zsh
            re.compile(r".*\$\s*$"),  # generic
        ]

        self.command_start_pattern = re.compile(r"^[^$#>%]*[$#>%]\s*(.+)$")

        self.emulator.on_output = self._handle_output
        self.emulator.on_exit = self._handle_exit

        self.on_command_start: Optional[Callable[[str], None]] = None
        self.on_command_end: Optional[Callable[[str, int], None]] = None
        self.on_directory_change: Optional[Callable[[str], None]] = None
        self.on_output: Optional[Callable[[str], None]] = None

        self._last_output_time = None
        self._output_buffer = ""

    def start(self):
        """터미널 시작"""
        self.emulator.start()

    def stop(self):
        """터미널 종료"""
        if self.command_running:
            self.history.cancel_command()

        self.emulator.stop()

    def execute(self, command: str):
        """명령어 실행"""
        if not command.strip():
            return

        self.current_command = command.strip()
        self.command_running = True

        self.history.start_command(self.current_command, self.current_directory)

        if self.on_command_start:
            self.on_command_start(self.current_command)

        self.emulator.write_text(command + "\n")

    def write_text(self, text: str):
        """터미널에 텍스트 입력"""
        self.emulator.write_text(text)

    def resize(self, cols: int, rows: int):
        """터미널 크기 조정"""
        self.emulator.resize(cols, rows)

    def is_running(self) -> bool:
        """터미널이 실행 중인지 확인"""
        return self.emulator.is_running()

    def get_output(self, lines: int = -1) -> List[str]:
        """출력 가져오기"""
        return self.buffer.get_lines(lines)

    def get_plain_output(self, lines: int = -1) -> str:
        """ANSI 코드가 제거된 출력 가져오기"""
        return self.buffer.get_plain_text(lines)

    def clear_output(self):
        """출력 버퍼 초기화"""
        self.buffer.clear()

    def get_command_history(self, count: int = 10):
        """명령어 히스토리 가져오기"""
        return self.history.get_recent(count)

    def search_history(self, pattern: str):
        """히스토리 검색"""
        return self.history.search(pattern)

    def get_current_directory(self) -> str:
        """현재 디렉토리 가져오기"""
        return self.current_directory

    def _handle_output(self, data: bytes):
        """출력 처리"""
        self.buffer.append(data)

        try:
            text = data.decode("utf-8", errors="replace")
        except UnicodeDecodeError:
            text = data.decode("latin-1", errors="replace")

        self._output_buffer += text

        self._detect_directory_change(text)

        if self.command_running:
            if self._is_prompt_line(text):
                self._end_command(0)  # 성공으로 가정

        if self.on_output:
            self.on_output(text)

    def _handle_exit(self, exit_code: int):
        """프로세스 종료 처리"""
        if self.command_running:
            self._end_command(exit_code)

    def _end_command(self, exit_code: int):
        """명령어 종료 처리"""
        if not self.command_running:
            return

        self.command_running = False

        output = self._output_buffer.strip()
        self._output_buffer = ""

        error = None
        if exit_code != 0:
            lines = output.split("\n")
            if len(lines) > 1:
                error = "\n".join(lines[-3:])  # 마지막 3줄

        self.history.end_command(exit_code, output, error or "")

        if self.on_command_end:
            self.on_command_end(self.current_command, exit_code)

        self.current_command = ""

    def _is_prompt_line(self, text: str) -> bool:
        """프롬프트 라인인지 확인"""
        lines = text.strip().split("\n")
        if not lines:
            return False

        last_line = lines[-1].strip()
        if not last_line:
            return False

        for pattern in self.prompt_patterns:
            if pattern.match(last_line):
                return True

        return False

    def _detect_directory_change(self, text: str):
        """디렉토리 변경 감지"""
        if self.current_command.startswith("cd "):
            self._check_current_directory()
        elif "cd " in text:
            self._check_current_directory()

    def _check_current_directory(self):
        """현재 디렉토리 확인 및 업데이트"""
        try:
            new_directory = os.getcwd()
            if new_directory != self.current_directory:
                # old_directory = self.current_directory  # Unused variable
                self.current_directory = new_directory

                if self.on_directory_change:
                    self.on_directory_change(self.current_directory)

        except OSError:
            pass

    def get_status(self) -> dict:
        """터미널 상태 정보"""
        return {
            "running": self.is_running(),
            "command_running": self.command_running,
            "current_command": self.current_command,
            "current_directory": self.current_directory,
            "buffer_lines": self.buffer.get_line_count(),
            "history_count": self.history.get_command_count(),
            "last_command": self.history.get_last_command(),
        }

    def interrupt_command(self):
        """현재 명령어 중단 (Ctrl+C)"""
        if self.command_running:
            self.emulator.write_text("\x03")  # Ctrl+C

    def send_eof(self):
        """EOF 전송 (Ctrl+D)"""
        self.emulator.write_text("\x04")  # Ctrl+D

    def clear_screen(self):
        """화면 지우기"""
        self.emulator.write_text("\x0c")  # Ctrl+L

    def get_buffer_info(self) -> dict:
        """버퍼 정보"""
        return self.buffer.get_buffer_info()

    def get_history_statistics(self) -> dict:
        """히스토리 통계"""
        return self.history.get_statistics()

    def save_history(self, filepath: str):
        """히스토리 저장"""
        self.history.save(filepath)

    def load_history(self, filepath: str):
        """히스토리 로드"""
        self.history.load(filepath)

    def export_session(self, filepath: str):
        """세션 정보 내보내기"""
        session_data = {
            "status": self.get_status(),
            "output": self.get_plain_output(),
            "history": [cmd.to_dict() for cmd in self.history.get_all()],
            "statistics": self.get_history_statistics(),
        }

        import json

        with open(filepath, "w", encoding="utf-8") as f:
            json.dump(session_data, f, indent=2, ensure_ascii=False)
