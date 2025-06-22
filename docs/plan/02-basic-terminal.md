# 02. 기본 터미널 래퍼 구현

## 목표
PTY(Pseudo-Terminal)를 사용하여 실제 셸 프로세스를 실행하고, 입출력을 관리하는 터미널 에뮬레이터를 구현합니다.

## 핵심 개념

### PTY (Pseudo-Terminal)란?
- 가상 터미널 인터페이스로, 프로그램이 실제 터미널처럼 동작할 수 있게 함
- Master-Slave 구조: Master는 우리 프로그램, Slave는 셸 프로세스
- 터미널 제어 시퀀스(색상, 커서 이동 등)를 그대로 전달

## Step 1: 기본 터미널 에뮬레이터 클래스

### terminal/emulator.py
```python
import os
import pty
import select
import subprocess
import threading
from typing import Callable, Optional, List
import struct
import fcntl
import termios


class TerminalEmulator:
    """PTY 기반 터미널 에뮬레이터"""

    def __init__(self,
                 shell: str = None,
                 cwd: str = None,
                 env: dict = None):
        """
        Args:
            shell: 사용할 셸 (기본: $SHELL 또는 /bin/bash)
            cwd: 작업 디렉토리
            env: 환경 변수
        """
        self.shell = shell or os.environ.get('SHELL', '/bin/bash')
        self.cwd = cwd or os.getcwd()
        self.env = env or os.environ.copy()

        self.master_fd = None
        self.slave_fd = None
        self.process = None
        self.is_running = False

        # 콜백 함수들
        self.on_output: Optional[Callable[[bytes], None]] = None
        self.on_exit: Optional[Callable[[int], None]] = None

    def start(self):
        """터미널 프로세스 시작"""
        # PTY 생성
        self.master_fd, self.slave_fd = pty.openpty()

        # 터미널 크기 설정
        self._set_terminal_size(80, 24)

        # 셸 프로세스 실행
        self.process = subprocess.Popen(
            [self.shell],
            stdin=self.slave_fd,
            stdout=self.slave_fd,
            stderr=self.slave_fd,
            cwd=self.cwd,
            env=self.env,
            preexec_fn=os.setsid  # 새 세션 생성
        )

        self.is_running = True

        # 출력 읽기 스레드 시작
        self.reader_thread = threading.Thread(target=self._read_output)
        self.reader_thread.daemon = True
        self.reader_thread.start()

    def stop(self):
        """터미널 프로세스 종료"""
        self.is_running = False

        if self.process:
            self.process.terminate()
            self.process.wait()

        if self.master_fd:
            os.close(self.master_fd)
        if self.slave_fd:
            os.close(self.slave_fd)

    def write(self, data: bytes):
        """터미널에 입력 전송"""
        if self.master_fd and self.is_running:
            os.write(self.master_fd, data)

    def write_text(self, text: str):
        """문자열을 터미널에 전송"""
        self.write(text.encode('utf-8'))

    def _read_output(self):
        """백그라운드에서 터미널 출력 읽기"""
        while self.is_running:
            try:
                # select를 사용해 논블로킹 읽기
                r, _, _ = select.select([self.master_fd], [], [], 0.1)

                if r:
                    data = os.read(self.master_fd, 4096)
                    if data and self.on_output:
                        self.on_output(data)

            except OSError:
                break

        # 프로세스 종료 처리
        if self.process:
            exit_code = self.process.wait()
            if self.on_exit:
                self.on_exit(exit_code)

    def _set_terminal_size(self, cols: int, rows: int):
        """터미널 크기 설정"""
        if self.master_fd:
            size = struct.pack('HHHH', rows, cols, 0, 0)
            fcntl.ioctl(self.master_fd, termios.TIOCSWINSZ, size)

    def resize(self, cols: int, rows: int):
        """터미널 크기 변경"""
        self._set_terminal_size(cols, rows)

        # SIGWINCH 시그널 전송
        if self.process and self.process.pid:
            os.kill(self.process.pid, signal.SIGWINCH)
```

## Step 2: 출력 버퍼 관리

### terminal/buffer.py
```python
from collections import deque
from typing import List, Tuple
import re


class OutputBuffer:
    """터미널 출력 버퍼 관리"""

    def __init__(self, max_lines: int = 10000):
        self.lines: deque[str] = deque(maxlen=max_lines)
        self.current_line = ""

        # ANSI 이스케이프 시퀀스 패턴
        self.ansi_escape = re.compile(r'\x1B(?:[@-Z\\-_]|\[[0-?]*[ -/]*[@-~])')

    def append(self, data: bytes):
        """새 데이터 추가"""
        text = data.decode('utf-8', errors='replace')

        # 현재 라인에 추가
        self.current_line += text

        # 줄바꿈 처리
        while '\n' in self.current_line:
            line, self.current_line = self.current_line.split('\n', 1)
            self.lines.append(line)

        # 캐리지 리턴 처리
        if '\r' in self.current_line:
            parts = self.current_line.split('\r')
            self.current_line = parts[-1]

    def get_lines(self, start: int = 0, count: int = -1) -> List[str]:
        """버퍼에서 라인 가져오기"""
        lines = list(self.lines)

        if self.current_line:
            lines.append(self.current_line)

        if count == -1:
            return lines[start:]
        else:
            return lines[start:start + count]

    def get_plain_text(self) -> str:
        """ANSI 코드가 제거된 평문 텍스트"""
        lines = self.get_lines()
        plain_lines = []

        for line in lines:
            plain_line = self.ansi_escape.sub('', line)
            plain_lines.append(plain_line)

        return '\n'.join(plain_lines)

    def clear(self):
        """버퍼 초기화"""
        self.lines.clear()
        self.current_line = ""

    def search(self, pattern: str) -> List[Tuple[int, str]]:
        """패턴 검색"""
        results = []
        lines = list(self.lines)

        for i, line in enumerate(lines):
            if pattern in line:
                results.append((i, line))

        return results
```

## Step 3: 명령어 히스토리 관리

### terminal/history.py
```python
from datetime import datetime
from typing import List, Optional, Dict, Any
from dataclasses import dataclass
import json


@dataclass
class Command:
    """실행된 명령어 정보"""
    command: str
    timestamp: datetime
    directory: str
    exit_code: Optional[int] = None
    output: Optional[str] = None
    error: Optional[str] = None
    duration: Optional[float] = None

    def to_dict(self) -> Dict[str, Any]:
        return {
            'command': self.command,
            'timestamp': self.timestamp.isoformat(),
            'directory': self.directory,
            'exit_code': self.exit_code,
            'output': self.output,
            'error': self.error,
            'duration': self.duration
        }


class CommandHistory:
    """명령어 히스토리 관리"""

    def __init__(self, max_size: int = 1000):
        self.history: List[Command] = []
        self.max_size = max_size
        self.current_command: Optional[Command] = None
        self.start_time: Optional[datetime] = None

    def start_command(self, command: str, directory: str):
        """새 명령어 시작"""
        self.current_command = Command(
            command=command.strip(),
            timestamp=datetime.now(),
            directory=directory
        )
        self.start_time = datetime.now()

    def end_command(self, exit_code: int, output: str = None, error: str = None):
        """명령어 종료"""
        if self.current_command and self.start_time:
            self.current_command.exit_code = exit_code
            self.current_command.output = output
            self.current_command.error = error
            self.current_command.duration = (
                datetime.now() - self.start_time
            ).total_seconds()

            self.history.append(self.current_command)

            # 크기 제한
            if len(self.history) > self.max_size:
                self.history = self.history[-self.max_size:]

            self.current_command = None
            self.start_time = None

    def get_recent(self, count: int = 10) -> List[Command]:
        """최근 명령어 가져오기"""
        return self.history[-count:]

    def search(self, pattern: str) -> List[Command]:
        """명령어 검색"""
        results = []
        for cmd in self.history:
            if pattern in cmd.command:
                results.append(cmd)
        return results

    def get_errors(self) -> List[Command]:
        """에러가 발생한 명령어들"""
        return [cmd for cmd in self.history if cmd.exit_code != 0]

    def save(self, filepath: str):
        """히스토리 저장"""
        data = [cmd.to_dict() for cmd in self.history]
        with open(filepath, 'w') as f:
            json.dump(data, f, indent=2)

    def load(self, filepath: str):
        """히스토리 로드"""
        with open(filepath, 'r') as f:
            data = json.load(f)

        self.history = []
        for item in data:
            cmd = Command(
                command=item['command'],
                timestamp=datetime.fromisoformat(item['timestamp']),
                directory=item['directory'],
                exit_code=item.get('exit_code'),
                output=item.get('output'),
                error=item.get('error'),
                duration=item.get('duration')
            )
            self.history.append(cmd)
```

## Step 4: 통합 터미널 매니저

### terminal/manager.py
```python
import os
import re
from typing import Optional, Callable
from .emulator import TerminalEmulator
from .buffer import OutputBuffer
from .history import CommandHistory


class TerminalManager:
    """터미널 기능 통합 관리"""

    def __init__(self):
        self.emulator = TerminalEmulator()
        self.buffer = OutputBuffer()
        self.history = CommandHistory()

        # 현재 상태
        self.current_directory = os.getcwd()
        self.current_command = ""
        self.command_running = False

        # 프롬프트 패턴 (bash/zsh)
        self.prompt_pattern = re.compile(r'.*[$#]\s*$')

        # 콜백 설정
        self.emulator.on_output = self._handle_output
        self.emulator.on_exit = self._handle_exit

        # 외부 콜백
        self.on_command_start: Optional[Callable[[str], None]] = None
        self.on_command_end: Optional[Callable[[str, int], None]] = None
        self.on_directory_change: Optional[Callable[[str], None]] = None

    def start(self):
        """터미널 시작"""
        self.emulator.start()

    def stop(self):
        """터미널 종료"""
        self.emulator.stop()

    def execute(self, command: str):
        """명령어 실행"""
        if command.strip():
            self.current_command = command
            self.command_running = True

            # 히스토리에 시작 기록
            self.history.start_command(command, self.current_directory)

            # 콜백 호출
            if self.on_command_start:
                self.on_command_start(command)

            # 명령어 전송
            self.emulator.write_text(command + '\n')

    def _handle_output(self, data: bytes):
        """출력 처리"""
        # 버퍼에 추가
        self.buffer.append(data)

        # 디렉토리 변경 감지
        text = data.decode('utf-8', errors='replace')
        self._detect_directory_change(text)

        # 프롬프트 감지 (명령어 종료)
        if self.command_running and self.prompt_pattern.search(text):
            self._end_command(0)  # 성공으로 가정

    def _handle_exit(self, exit_code: int):
        """프로세스 종료 처리"""
        if self.command_running:
            self._end_command(exit_code)

    def _end_command(self, exit_code: int):
        """명령어 종료 처리"""
        if self.command_running:
            self.command_running = False

            # 출력 수집
            output = self.buffer.get_plain_text()

            # 히스토리에 종료 기록
            self.history.end_command(exit_code, output)

            # 콜백 호출
            if self.on_command_end:
                self.on_command_end(self.current_command, exit_code)

            self.current_command = ""

    def _detect_directory_change(self, text: str):
        """디렉토리 변경 감지"""
        # PWD 변경 감지 (간단한 휴리스틱)
        if 'cd ' in text or self.current_command.startswith('cd '):
            # pwd 명령으로 현재 디렉토리 확인
            self.emulator.write_text('pwd\n')

    def get_output(self, lines: int = -1) -> List[str]:
        """출력 가져오기"""
        if lines == -1:
            return self.buffer.get_lines()
        else:
            return self.buffer.get_lines(-lines)

    def clear_output(self):
        """출력 버퍼 초기화"""
        self.buffer.clear()

    def resize(self, cols: int, rows: int):
        """터미널 크기 조정"""
        self.emulator.resize(cols, rows)
```

## Step 5: 테스트 구현

### test_terminal.py
```python
#!/usr/bin/env python3
import time
import sys
from terminal.manager import TerminalManager


def test_basic_terminal():
    """기본 터미널 기능 테스트"""
    print("=== 터미널 에뮬레이터 테스트 ===\n")

    # 터미널 매니저 생성
    tm = TerminalManager()

    # 콜백 설정
    def on_command_start(cmd):
        print(f"[실행 시작] {cmd}")

    def on_command_end(cmd, exit_code):
        print(f"[실행 완료] {cmd} (exit: {exit_code})")

    tm.on_command_start = on_command_start
    tm.on_command_end = on_command_end

    # 터미널 시작
    tm.start()
    print("터미널이 시작되었습니다.\n")

    # 테스트 명령어들
    test_commands = [
        "echo 'Hello from Terminal Emulator!'",
        "pwd",
        "ls -la",
        "echo $SHELL",
        "date",
        "python3 --version"
    ]

    # 명령어 실행
    for cmd in test_commands:
        print(f"\n실행할 명령어: {cmd}")
        tm.execute(cmd)
        time.sleep(1)  # 출력 대기

        # 최근 출력 표시
        output = tm.get_output(5)
        print("출력:")
        for line in output[-5:]:
            print(f"  {line}")

    # 히스토리 확인
    print("\n\n=== 명령어 히스토리 ===")
    for cmd in tm.history.get_recent(10):
        print(f"- {cmd.command} (실행시간: {cmd.duration:.2f}초)")

    # 종료
    tm.stop()
    print("\n터미널이 종료되었습니다.")


def test_interactive():
    """대화형 테스트"""
    print("=== 대화형 터미널 테스트 ===")
    print("명령어를 입력하세요. 종료하려면 'exit'를 입력하세요.\n")

    tm = TerminalManager()

    # 실시간 출력 표시
    def handle_output(data: bytes):
        sys.stdout.write(data.decode('utf-8', errors='replace'))
        sys.stdout.flush()

    tm.emulator.on_output = handle_output
    tm.start()

    try:
        while True:
            # 입력 대기
            cmd = input()

            if cmd.lower() == 'exit':
                break

            tm.execute(cmd)
            time.sleep(0.5)  # 출력 완료 대기

    except KeyboardInterrupt:
        pass

    tm.stop()
    print("\n대화형 테스트 종료")


if __name__ == "__main__":
    # 기본 테스트
    test_basic_terminal()

    # 대화형 테스트 (선택사항)
    print("\n대화형 테스트를 실행하시겠습니까? (y/n): ", end='')
    if input().lower() == 'y':
        test_interactive()
```

## Checkpoint 1: 터미널 래퍼 테스트

### 실행 방법
```bash
# 터미널 모듈이 있는 디렉토리에서
python test_terminal.py
```

### 체크리스트
- [ ] 터미널 프로세스가 정상적으로 시작됨
- [ ] echo, pwd, ls 등 기본 명령어 실행됨
- [ ] 명령어 출력이 올바르게 캡처됨
- [ ] 명령어 히스토리가 기록됨
- [ ] 터미널이 정상적으로 종료됨
- [ ] 한글 출력이 깨지지 않음
- [ ] ANSI 컬러 코드가 포함된 출력 처리됨

### 예상 출력
```
=== 터미널 에뮬레이터 테스트 ===

터미널이 시작되었습니다.

실행할 명령어: echo 'Hello from Terminal Emulator!'
[실행 시작] echo 'Hello from Terminal Emulator!'
[실행 완료] echo 'Hello from Terminal Emulator!' (exit: 0)
출력:
  Hello from Terminal Emulator!

실행할 명령어: pwd
[실행 시작] pwd
[실행 완료] pwd (exit: 0)
출력:
  /Users/username/project/test-tui

...
```

## 문제 해결

### 1. PTY 권한 오류
```python
# 오류: [Errno 13] Permission denied: '/dev/ptmx'
# 해결: 권한 확인
ls -la /dev/ptmx
# crw-rw-rw- 형태여야 함
```

### 2. 인코딩 오류
```python
# emulator.py에서 decode 시 errors='replace' 사용
text = data.decode('utf-8', errors='replace')
```

### 3. 프롬프트 감지 실패
```python
# 다양한 프롬프트 패턴 지원
self.prompt_patterns = [
    re.compile(r'.*[$#]\s*$'),  # bash/sh
    re.compile(r'.*[>]\s*$'),   # fish
    re.compile(r'.*[%]\s*$'),   # zsh
]
```

## 다음 단계

터미널 래퍼가 정상적으로 작동하면 [03-tui-framework.md](03-tui-framework.md)로 진행하여 Textual UI를 구축합니다.
