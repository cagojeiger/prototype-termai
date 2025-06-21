import json
import os
from dataclasses import dataclass
from datetime import datetime
from typing import Any, Dict, List, Optional


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
        """Convert command to dictionary for JSON serialization"""
        return {
            "command": self.command,
            "timestamp": self.timestamp.isoformat(),
            "directory": self.directory,
            "exit_code": self.exit_code,
            "output": self.output,
            "error": self.error,
            "duration": self.duration,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "Command":
        """Create Command from dictionary"""
        timestamp = datetime.fromisoformat(data["timestamp"])

        return cls(
            command=data["command"],
            timestamp=timestamp,
            directory=data["directory"],
            exit_code=data.get("exit_code"),
            output=data.get("output"),
            error=data.get("error"),
            duration=data.get("duration"),
        )

    def is_error(self) -> bool:
        """Check if command resulted in an error"""
        return self.exit_code is not None and self.exit_code != 0

    def get_duration_ms(self) -> Optional[float]:
        """Get duration in milliseconds"""
        return self.duration * 1000 if self.duration is not None else None


class CommandHistory:
    """명령어 히스토리 관리"""

    def __init__(self, max_size: int = 1000):
        self.history: List[Command] = []
        self.max_size = max_size
        self.current_command: Optional[Command] = None
        self.start_time: Optional[datetime] = None

    def start_command(self, command: str, directory: str = None):
        """새 명령어 시작"""
        if directory is None:
            directory = os.getcwd()

        self.current_command = Command(
            command=command.strip(), timestamp=datetime.now(), directory=directory
        )
        self.start_time = datetime.now()

    def end_command(self, exit_code: int, output: str = None, error: str = None):
        """명령어 종료"""
        if self.current_command and self.start_time:
            end_time = datetime.now()
            duration = (end_time - self.start_time).total_seconds()

            self.current_command.exit_code = exit_code
            self.current_command.output = output
            self.current_command.error = error
            self.current_command.duration = duration

            self.history.append(self.current_command)

            if len(self.history) > self.max_size:
                self.history = self.history[-self.max_size :]

            self.current_command = None
            self.start_time = None

    def cancel_command(self):
        """Cancel current command without adding to history"""
        self.current_command = None
        self.start_time = None

    def get_recent(self, count: int = 10) -> List[Command]:
        """최근 명령어 가져오기"""
        if count <= 0:
            return []
        return self.history[-count:]

    def get_all(self) -> List[Command]:
        """모든 명령어 가져오기"""
        return self.history.copy()

    def search(self, pattern: str, case_sensitive: bool = False) -> List[Command]:
        """명령어 검색"""
        results = []
        search_pattern = pattern if case_sensitive else pattern.lower()

        for cmd in self.history:
            search_text = cmd.command if case_sensitive else cmd.command.lower()
            if search_pattern in search_text:
                results.append(cmd)

        return results

    def get_errors(self) -> List[Command]:
        """에러가 발생한 명령어들"""
        return [cmd for cmd in self.history if cmd.is_error()]

    def get_by_directory(self, directory: str) -> List[Command]:
        """특정 디렉토리에서 실행된 명령어들"""
        return [cmd for cmd in self.history if cmd.directory == directory]

    def get_commands_by_pattern(self, pattern: str) -> List[Command]:
        """패턴으로 명령어 필터링"""
        import re

        try:
            regex = re.compile(pattern, re.IGNORECASE)
            return [cmd for cmd in self.history if regex.search(cmd.command)]
        except re.error:
            return self.search(pattern, case_sensitive=False)

    def get_statistics(self) -> Dict[str, Any]:
        """히스토리 통계 정보"""
        if not self.history:
            return {
                "total_commands": 0,
                "error_count": 0,
                "success_count": 0,
                "error_rate": 0.0,
                "average_duration": 0.0,
                "most_used_commands": [],
            }

        total = len(self.history)
        errors = len(self.get_errors())
        success = total - errors

        durations = [cmd.duration for cmd in self.history if cmd.duration is not None]
        avg_duration = sum(durations) / len(durations) if durations else 0.0

        command_counts: dict = {}
        for cmd in self.history:
            base_cmd = cmd.command.split()[0] if cmd.command.split() else cmd.command
            command_counts[base_cmd] = command_counts.get(base_cmd, 0) + 1

        most_used = sorted(command_counts.items(), key=lambda x: x[1], reverse=True)[:5]

        return {
            "total_commands": total,
            "error_count": errors,
            "success_count": success,
            "error_rate": errors / total if total > 0 else 0.0,
            "average_duration": avg_duration,
            "most_used_commands": most_used,
        }

    def clear(self):
        """히스토리 초기화"""
        self.history.clear()
        self.current_command = None
        self.start_time = None

    def save(self, filepath: str):
        """히스토리를 JSON 파일로 저장"""
        data = [cmd.to_dict() for cmd in self.history]

        os.makedirs(os.path.dirname(filepath), exist_ok=True)

        with open(filepath, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2, ensure_ascii=False)

    def load(self, filepath: str):
        """JSON 파일에서 히스토리 로드"""
        if not os.path.exists(filepath):
            return

        try:
            with open(filepath, encoding="utf-8") as f:
                data = json.load(f)

            self.history = []
            for item in data:
                try:
                    cmd = Command.from_dict(item)
                    self.history.append(cmd)
                except (KeyError, ValueError):
                    continue

            if len(self.history) > self.max_size:
                self.history = self.history[-self.max_size :]

        except (OSError, json.JSONDecodeError):
            self.history = []

    def export_to_text(self, filepath: str, include_output: bool = False):
        """히스토리를 텍스트 파일로 내보내기"""
        with open(filepath, "w", encoding="utf-8") as f:
            f.write("Command History Export\n")
            f.write("=" * 50 + "\n\n")

            for i, cmd in enumerate(self.history, 1):
                f.write(f"{i}. {cmd.command}\n")
                f.write(f"   Time: {cmd.timestamp.strftime('%Y-%m-%d %H:%M:%S')}\n")
                f.write(f"   Directory: {cmd.directory}\n")
                f.write(f"   Exit Code: {cmd.exit_code}\n")
                if cmd.duration is not None:
                    f.write(f"   Duration: {cmd.duration:.3f}s\n")

                if include_output and cmd.output:
                    f.write("   Output:\n")
                    for line in cmd.output.split("\n"):
                        f.write(f"     {line}\n")

                if cmd.error:
                    f.write(f"   Error: {cmd.error}\n")

                f.write("\n")

    def get_current_command(self) -> Optional[Command]:
        """현재 실행 중인 명령어 정보"""
        return self.current_command

    def is_command_running(self) -> bool:
        """명령어가 현재 실행 중인지 확인"""
        return self.current_command is not None

    def get_last_command(self) -> Optional[Command]:
        """마지막으로 실행된 명령어"""
        return self.history[-1] if self.history else None

    def get_command_count(self) -> int:
        """총 명령어 개수"""
        return len(self.history)
