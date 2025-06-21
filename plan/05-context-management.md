# 05. 스마트 컨텍스트 관리 시스템

## 목표
실시간 터미널 환경에서 효율적으로 컨텍스트를 수집, 필터링, 압축하여 AI에게 가장 관련성 높은 정보만 전달합니다.

## 핵심 과제

### 1. 컨텍스트 윈도우 제한
- Ollama 모델의 토큰 제한 (4K-8K)
- 긴 세션에서 중요 정보 유지
- 관련성 낮은 정보 자동 제거

### 2. 실시간 성능
- 빠른 컨텍스트 평가
- 비동기 처리로 터미널 블로킹 방지
- 캐싱으로 반복 분석 최소화

## Step 1: 컨텍스트 구조 정의

### ai/context.py
```python
from dataclasses import dataclass, field
from datetime import datetime
from typing import List, Dict, Any, Optional, Tuple
from collections import deque
import hashlib
import json


@dataclass
class CommandContext:
    """명령어 실행 컨텍스트"""
    command: str
    timestamp: datetime
    directory: str
    exit_code: Optional[int] = None
    output: Optional[str] = None
    error: Optional[str] = None
    duration: Optional[float] = None
    relevance_score: float = 1.0
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "command": self.command,
            "timestamp": self.timestamp.isoformat(),
            "directory": self.directory,
            "exit_code": self.exit_code,
            "output": self.output[:500] if self.output else None,  # 출력 제한
            "error": self.error,
            "duration": self.duration,
            "relevance_score": self.relevance_score
        }
        
    def get_hash(self) -> str:
        """명령어 해시 (캐싱용)"""
        key = f"{self.command}:{self.directory}"
        return hashlib.md5(key.encode()).hexdigest()


@dataclass
class SessionContext:
    """세션 컨텍스트"""
    session_id: str
    start_time: datetime
    current_directory: str
    environment: Dict[str, str] = field(default_factory=dict)
    active_task: Optional[str] = None
    task_history: List[str] = field(default_factory=list)
    
    def add_task_marker(self, task: str):
        """작업 마커 추가"""
        self.active_task = task
        self.task_history.append(f"{datetime.now()}: {task}")


class ContextWindow:
    """스마트 컨텍스트 윈도우 관리"""
    
    def __init__(self, 
                 max_commands: int = 50,
                 max_tokens: int = 4096,
                 token_per_command: int = 100):
        self.max_commands = max_commands
        self.max_tokens = max_tokens
        self.token_per_command = token_per_command
        
        # 명령어 큐 (최신순)
        self.commands: deque[CommandContext] = deque(maxlen=max_commands)
        
        # 중요 명령어 보존
        self.important_commands: List[CommandContext] = []
        
        # 세션 정보
        self.session = SessionContext(
            session_id=self._generate_session_id(),
            start_time=datetime.now(),
            current_directory=""
        )
        
    def _generate_session_id(self) -> str:
        """세션 ID 생성"""
        return datetime.now().strftime("%Y%m%d_%H%M%S")
        
    def add_command(self, command: CommandContext):
        """명령어 추가"""
        # 관련성 점수 계산
        command.relevance_score = self._calculate_relevance(command)
        
        # 중요도가 높으면 보존
        if command.relevance_score >= 0.8:
            self.important_commands.append(command)
            
        # 일반 큐에 추가
        self.commands.append(command)
        
        # 디렉토리 업데이트
        self.session.current_directory = command.directory
        
    def _calculate_relevance(self, command: CommandContext) -> float:
        """명령어 관련성 점수 계산"""
        score = 0.5  # 기본 점수
        
        # 에러가 있으면 높은 점수
        if command.exit_code != 0 or command.error:
            score = 0.9
            
        # 특정 명령어 패턴
        important_patterns = [
            ("git", 0.7),
            ("npm", 0.7),
            ("pip", 0.7),
            ("docker", 0.8),
            ("kubectl", 0.8),
            ("sudo", 0.8),
            ("rm -rf", 0.9),
            ("curl", 0.6),
            ("wget", 0.6),
        ]
        
        cmd_lower = command.command.lower()
        for pattern, pattern_score in important_patterns:
            if pattern in cmd_lower:
                score = max(score, pattern_score)
                
        # 네비게이션 명령어는 낮은 점수
        if cmd_lower in ["ls", "pwd", "cd", "clear", "echo"]:
            score = min(score, 0.3)
            
        # 현재 작업과 관련있으면 높은 점수
        if self.session.active_task:
            task_keywords = self.session.active_task.lower().split()
            if any(keyword in cmd_lower for keyword in task_keywords):
                score = max(score, 0.7)
                
        return score
        
    def get_context(self, 
                   include_all: bool = False,
                   max_tokens: Optional[int] = None) -> Dict[str, Any]:
        """AI를 위한 컨텍스트 생성"""
        max_tokens = max_tokens or self.max_tokens
        
        # 토큰 예산 관리
        token_budget = max_tokens
        context_commands = []
        
        # 1. 중요 명령어 우선 포함
        for cmd in reversed(self.important_commands[-10:]):  # 최근 10개
            if token_budget >= self.token_per_command:
                context_commands.append(cmd)
                token_budget -= self.token_per_command
                
        # 2. 최근 명령어 추가
        for cmd in reversed(self.commands):
            if cmd not in context_commands and token_budget >= self.token_per_command:
                if include_all or cmd.relevance_score >= 0.5:
                    context_commands.append(cmd)
                    token_budget -= self.token_per_command
                    
        # 시간순 정렬
        context_commands.sort(key=lambda x: x.timestamp)
        
        return {
            "session_id": self.session.session_id,
            "current_directory": self.session.current_directory,
            "active_task": self.session.active_task,
            "commands": [cmd.to_dict() for cmd in context_commands],
            "summary": self._generate_summary(),
            "token_usage": max_tokens - token_budget
        }
        
    def _generate_summary(self) -> str:
        """세션 요약 생성"""
        # 최근 에러
        recent_errors = [
            cmd for cmd in list(self.commands)[-10:]
            if cmd.exit_code != 0
        ]
        
        # 주요 작업
        main_commands = [
            cmd.command.split()[0] 
            for cmd in self.commands
            if cmd.relevance_score >= 0.7
        ]
        
        command_frequency = {}
        for cmd in main_commands:
            command_frequency[cmd] = command_frequency.get(cmd, 0) + 1
            
        top_commands = sorted(
            command_frequency.items(), 
            key=lambda x: x[1], 
            reverse=True
        )[:5]
        
        summary = f"Session: {self.session.session_id}\n"
        summary += f"Duration: {(datetime.now() - self.session.start_time).seconds}s\n"
        summary += f"Errors: {len(recent_errors)}\n"
        summary += f"Main activities: {', '.join([cmd for cmd, _ in top_commands])}"
        
        return summary
        
    def mark_task(self, task_description: str):
        """작업 마커 설정"""
        self.session.add_task_marker(task_description)
        
    def clear_old_commands(self, keep_important: bool = True):
        """오래된 명령어 정리"""
        if not keep_important:
            self.important_commands.clear()
            
        # 관련성 낮은 명령어 제거
        self.commands = deque(
            [cmd for cmd in self.commands if cmd.relevance_score >= 0.4],
            maxlen=self.max_commands
        )
```

## Step 2: 컨텍스트 필터링 시스템

### ai/filters.py
```python
import re
from typing import List, Dict, Any, Set
from dataclasses import dataclass


@dataclass
class FilterRule:
    """필터링 규칙"""
    name: str
    pattern: str
    action: str  # "remove", "mask", "truncate"
    priority: int = 5
    
    def apply(self, text: str) -> str:
        """필터 적용"""
        if self.action == "remove":
            return re.sub(self.pattern, "", text)
        elif self.action == "mask":
            return re.sub(self.pattern, "[MASKED]", text)
        elif self.action == "truncate":
            match = re.search(self.pattern, text)
            if match:
                return text[:match.start()] + "...[truncated]"
        return text


class ContextFilter:
    """컨텍스트 필터링"""
    
    def __init__(self):
        self.filters = self._init_default_filters()
        
    def _init_default_filters(self) -> List[FilterRule]:
        """기본 필터 설정"""
        return [
            # 민감 정보 필터
            FilterRule(
                name="api_keys",
                pattern=r"(api[_-]?key|apikey|api[_-]?secret)['\"]?\s*[:=]\s*['\"]?[\w-]+",
                action="mask",
                priority=10
            ),
            FilterRule(
                name="passwords",
                pattern=r"(password|passwd|pwd)['\"]?\s*[:=]\s*['\"]?[\w@#$%^&*]+",
                action="mask",
                priority=10
            ),
            FilterRule(
                name="tokens",
                pattern=r"(token|auth[_-]?token|bearer)['\"]?\s*[:=]\s*['\"]?[\w-]+",
                action="mask",
                priority=10
            ),
            
            # 노이즈 제거
            FilterRule(
                name="ansi_codes",
                pattern=r"\x1b\[[0-9;]*[mGKH]",
                action="remove",
                priority=5
            ),
            FilterRule(
                name="progress_bars",
                pattern=r"[━█▓▒░]+\s*\d+%",
                action="remove",
                priority=3
            ),
            
            # 긴 출력 자르기
            FilterRule(
                name="long_lists",
                pattern=r"(^.+\n){50,}",  # 50줄 이상
                action="truncate",
                priority=7
            ),
        ]
        
    def filter_command_output(self, output: str) -> str:
        """명령어 출력 필터링"""
        filtered = output
        
        # 우선순위 순으로 필터 적용
        for filter_rule in sorted(self.filters, key=lambda x: x.priority, reverse=True):
            filtered = filter_rule.apply(filtered)
            
        return filtered
        
    def filter_context(self, context: Dict[str, Any]) -> Dict[str, Any]:
        """전체 컨텍스트 필터링"""
        filtered_context = context.copy()
        
        # 명령어 필터링
        if "commands" in filtered_context:
            for cmd in filtered_context["commands"]:
                if cmd.get("output"):
                    cmd["output"] = self.filter_command_output(cmd["output"])
                if cmd.get("error"):
                    cmd["error"] = self.filter_command_output(cmd["error"])
                    
        return filtered_context
        
    def add_filter(self, filter_rule: FilterRule):
        """필터 추가"""
        self.filters.append(filter_rule)
        
    def remove_filter(self, name: str):
        """필터 제거"""
        self.filters = [f for f in self.filters if f.name != name]
```

## Step 3: 컨텍스트 매니저 통합

### ai/context_manager.py
```python
import asyncio
from typing import Dict, Any, Optional, List
from datetime import datetime, timedelta
import json
import logging

from .context import ContextWindow, CommandContext
from .filters import ContextFilter
from .triggers import TriggerManager
from ..terminal.manager import TerminalManager

logger = logging.getLogger(__name__)


class ContextManager:
    """통합 컨텍스트 관리자"""
    
    def __init__(self, terminal_manager: TerminalManager):
        self.terminal_manager = terminal_manager
        self.context_window = ContextWindow()
        self.filter = ContextFilter()
        self.trigger_manager = TriggerManager()
        
        # 캐시
        self.analysis_cache: Dict[str, Any] = {}
        self.cache_ttl = timedelta(minutes=5)
        
        # 콜백 설정
        self._setup_callbacks()
        
    def _setup_callbacks(self):
        """터미널 콜백 설정"""
        self.terminal_manager.on_command_start = self._on_command_start
        self.terminal_manager.on_command_end = self._on_command_end
        self.terminal_manager.on_directory_change = self._on_directory_change
        
    def _on_command_start(self, command: str):
        """명령어 시작 처리"""
        logger.info(f"Command started: {command}")
        
    def _on_command_end(self, command: str, exit_code: int):
        """명령어 종료 처리"""
        # 출력 수집
        output_lines = self.terminal_manager.get_output(100)  # 최근 100줄
        output = "\n".join(output_lines)
        
        # 에러 추출
        error = ""
        if exit_code != 0:
            # 에러 패턴 찾기
            error_patterns = [
                r"error:.*",
                r"fatal:.*",
                r"warning:.*",
                r"failed.*",
                r"cannot.*",
                r"unable.*"
            ]
            
            for line in output_lines:
                for pattern in error_patterns:
                    if re.search(pattern, line, re.IGNORECASE):
                        error += line + "\n"
                        
        # 컨텍스트 생성
        cmd_context = CommandContext(
            command=command,
            timestamp=datetime.now(),
            directory=self.terminal_manager.current_directory,
            exit_code=exit_code,
            output=output,
            error=error
        )
        
        # 컨텍스트 추가
        self.context_window.add_command(cmd_context)
        
        # 트리거 확인
        self._check_triggers(cmd_context)
        
    def _on_directory_change(self, new_dir: str):
        """디렉토리 변경 처리"""
        self.context_window.session.current_directory = new_dir
        
    def _check_triggers(self, cmd_context: CommandContext):
        """AI 트리거 확인"""
        context_dict = cmd_context.to_dict()
        trigger = self.trigger_manager.should_trigger(context_dict)
        
        if trigger:
            logger.info(f"Trigger activated: {trigger.description}")
            # AI 분석 요청 (비동기)
            asyncio.create_task(self._request_ai_analysis(trigger))
            
    async def _request_ai_analysis(self, trigger):
        """AI 분석 요청"""
        # 캐시 확인
        cache_key = self._get_cache_key()
        if cache_key in self.analysis_cache:
            cached = self.analysis_cache[cache_key]
            if datetime.now() - cached["timestamp"] < self.cache_ttl:
                logger.info("Using cached analysis")
                return cached["result"]
                
        # 컨텍스트 생성
        context = self.get_filtered_context()
        
        # AI 분석 요청 (실제 구현은 UI에서)
        # 여기서는 이벤트만 발생
        logger.info(f"Requesting AI analysis for trigger: {trigger.description}")
        
    def _get_cache_key(self) -> str:
        """캐시 키 생성"""
        recent_commands = list(self.context_window.commands)[-5:]
        key_parts = [cmd.get_hash() for cmd in recent_commands]
        return ":".join(key_parts)
        
    def get_filtered_context(self, include_all: bool = False) -> Dict[str, Any]:
        """필터링된 컨텍스트 가져오기"""
        # 원본 컨텍스트
        context = self.context_window.get_context(include_all)
        
        # 필터 적용
        filtered = self.filter.filter_context(context)
        
        return filtered
        
    def mark_task(self, task: str):
        """작업 마커 설정"""
        self.context_window.mark_task(task)
        logger.info(f"Task marked: {task}")
        
    def get_suggestions(self) -> List[str]:
        """현재 컨텍스트 기반 제안"""
        suggestions = []
        
        # 최근 에러 기반 제안
        recent_commands = list(self.context_window.commands)[-10:]
        for cmd in recent_commands:
            if cmd.exit_code != 0:
                if "git" in cmd.command:
                    suggestions.append("git status  # Check repository status")
                elif "npm" in cmd.command:
                    suggestions.append("npm install  # Install dependencies")
                elif "python" in cmd.command:
                    suggestions.append("pip install -r requirements.txt")
                    
        # 현재 디렉토리 기반 제안
        cwd = self.context_window.session.current_directory
        if "package.json" in self.terminal_manager.execute("ls"):
            suggestions.append("npm test  # Run tests")
        elif "requirements.txt" in self.terminal_manager.execute("ls"):
            suggestions.append("python -m pytest  # Run tests")
            
        return suggestions[:5]  # 최대 5개
        
    def export_session(self, filepath: str):
        """세션 내보내기"""
        session_data = {
            "session": self.context_window.session.__dict__,
            "commands": [cmd.to_dict() for cmd in self.context_window.commands],
            "important_commands": [cmd.to_dict() for cmd in self.context_window.important_commands],
            "timestamp": datetime.now().isoformat()
        }
        
        with open(filepath, 'w') as f:
            json.dump(session_data, f, indent=2)
            
        logger.info(f"Session exported to {filepath}")
```

## Step 4: 통합 테스트

### test_context.py
```python
#!/usr/bin/env python3
import asyncio
from datetime import datetime
import json

from ai.context import ContextWindow, CommandContext
from ai.filters import ContextFilter, FilterRule
from ai.context_manager import ContextManager
from terminal.manager import TerminalManager


def test_relevance_scoring():
    """관련성 점수 테스트"""
    print("=== 관련성 점수 테스트 ===\n")
    
    window = ContextWindow()
    
    # 테스트 명령어들
    test_commands = [
        ("ls -la", 0, None),  # 낮은 점수
        ("git commit -m 'fix'", 0, None),  # 중간 점수
        ("npm install", 1, "npm ERR! Failed"),  # 높은 점수 (에러)
        ("rm -rf node_modules", 0, None),  # 높은 점수 (위험)
        ("cd ..", 0, None),  # 낮은 점수
    ]
    
    for cmd, exit_code, error in test_commands:
        context = CommandContext(
            command=cmd,
            timestamp=datetime.now(),
            directory="/home/user/project",
            exit_code=exit_code,
            error=error
        )
        window.add_command(context)
        print(f"{cmd}: 관련성 점수 = {context.relevance_score:.2f}")
        
    print(f"\n중요 명령어 수: {len(window.important_commands)}")


def test_filtering():
    """필터링 테스트"""
    print("\n=== 필터링 테스트 ===\n")
    
    filter = ContextFilter()
    
    # 테스트 케이스
    test_cases = [
        ("API_KEY=abc123 curl https://api.example.com", "민감 정보"),
        ("password: mysecret123", "패스워드"),
        ("\x1b[32mGreen text\x1b[0m", "ANSI 코드"),
        ("█████████ 100%", "프로그레스 바"),
    ]
    
    for text, description in test_cases:
        filtered = filter.filter_command_output(text)
        print(f"{description}:")
        print(f"  원본: {repr(text)}")
        print(f"  필터: {repr(filtered)}\n")


def test_context_window():
    """컨텍스트 윈도우 테스트"""
    print("=== 컨텍스트 윈도우 테스트 ===\n")
    
    window = ContextWindow(max_commands=10, max_tokens=1000)
    
    # 많은 명령어 추가
    for i in range(20):
        cmd = CommandContext(
            command=f"command_{i}",
            timestamp=datetime.now(),
            directory="/home/user",
            exit_code=0 if i % 3 else 1  # 3개마다 에러
        )
        window.add_command(cmd)
        
    # 컨텍스트 생성
    context = window.get_context()
    
    print(f"전체 명령어 수: 20")
    print(f"윈도우 명령어 수: {len(window.commands)}")
    print(f"컨텍스트 명령어 수: {len(context['commands'])}")
    print(f"토큰 사용량: {context['token_usage']}")
    print(f"\n요약:\n{context['summary']}")


async def test_context_manager():
    """컨텍스트 매니저 통합 테스트"""
    print("\n=== 컨텍스트 매니저 테스트 ===\n")
    
    # 터미널 매니저 생성
    tm = TerminalManager()
    cm = ContextManager(tm)
    
    # 작업 마커 설정
    cm.mark_task("Git 커밋 작업")
    
    # 가상의 명령어 실행 시뮬레이션
    commands = [
        ("git status", 0, "On branch main\nnothing to commit"),
        ("git add .", 0, ""),
        ("git commit -m 'Update'", 1, "error: no changes added to commit"),
        ("git add -A", 0, ""),
        ("git commit -m 'Update'", 0, "1 file changed"),
    ]
    
    for cmd, exit_code, output in commands:
        # 명령어 시작
        cm._on_command_start(cmd)
        
        # 명령어 종료
        cm._on_command_end(cmd, exit_code)
        
        # 출력 시뮬레이션 (실제로는 터미널에서 제공)
        context = CommandContext(
            command=cmd,
            timestamp=datetime.now(),
            directory="/home/user/project",
            exit_code=exit_code,
            output=output
        )
        cm.context_window.add_command(context)
        
    # 필터링된 컨텍스트 가져오기
    filtered_context = cm.get_filtered_context()
    
    print("컨텍스트 내용:")
    print(json.dumps(filtered_context, indent=2, default=str))
    
    # 제안 가져오기
    suggestions = cm.get_suggestions()
    print("\n제안사항:")
    for suggestion in suggestions:
        print(f"  - {suggestion}")


def main():
    """메인 테스트 함수"""
    test_relevance_scoring()
    test_filtering()
    test_context_window()
    asyncio.run(test_context_manager())
    
    print("\n모든 테스트 완료!")


if __name__ == "__main__":
    main()
```

## 문제 해결

### 1. 메모리 사용량 증가
```python
# 주기적으로 오래된 컨텍스트 정리
window.clear_old_commands(keep_important=True)

# 캐시 크기 제한
max_cache_size = 100
if len(cache) > max_cache_size:
    # 오래된 캐시 제거
    oldest_keys = sorted(cache.keys())[:50]
    for key in oldest_keys:
        del cache[key]
```

### 2. 느린 관련성 계산
```python
# 패턴 매칭 최적화
import re
compiled_patterns = {
    pattern: re.compile(pattern, re.IGNORECASE)
    for pattern in important_patterns
}

# 병렬 처리
from concurrent.futures import ThreadPoolExecutor
with ThreadPoolExecutor(max_workers=4) as executor:
    scores = executor.map(calculate_relevance, commands)
```

### 3. 컨텍스트 크기 초과
```python
# 동적 토큰 할당
if total_tokens > max_tokens:
    # 관련성 낮은 명령어부터 제거
    sorted_commands = sorted(commands, key=lambda x: x.relevance_score)
    while total_tokens > max_tokens and sorted_commands:
        removed = sorted_commands.pop(0)
        total_tokens -= estimate_tokens(removed)
```

## 다음 단계

스마트 컨텍스트 시스템이 구축되면 [06-realtime-features.md](06-realtime-features.md)로 진행하여 실시간 기능을 구현합니다.