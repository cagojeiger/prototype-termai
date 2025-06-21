# 04. Ollama API 통합

## 목표
Ollama API를 통해 로컬 LLM과 통신하고, 터미널 컨텍스트를 분석하여 지능적인 도움을 제공합니다.

## Ollama API 개요

### 주요 엔드포인트
- `/api/generate`: 텍스트 생성
- `/api/chat`: 대화형 응답
- `/api/tags`: 사용 가능한 모델 목록
- `/api/embeddings`: 임베딩 생성

### 스트리밍 응답
Ollama는 실시간 스트리밍을 지원하여 긴 응답도 즉시 표시 가능

## Step 1: Ollama 클라이언트 구현

### ai/ollama_client.py
```python
import httpx
import json
import asyncio
from typing import AsyncGenerator, Dict, Any, Optional, List
from dataclasses import dataclass
from datetime import datetime
import logging

logger = logging.getLogger(__name__)


@dataclass
class OllamaConfig:
    """Ollama 설정"""
    host: str = "http://localhost:11434"
    model: str = "codellama:7b"
    timeout: int = 30
    temperature: float = 0.7
    max_tokens: int = 500
    context_window: int = 4096


@dataclass
class AIResponse:
    """AI 응답 구조"""
    content: str
    suggestions: List[str]
    warnings: List[str]
    errors: List[str]
    model: str
    timestamp: datetime
    processing_time: float


class OllamaClient:
    """Ollama API 클라이언트"""

    def __init__(self, config: OllamaConfig = None):
        self.config = config or OllamaConfig()
        self.client = httpx.AsyncClient(timeout=self.config.timeout)

    async def check_health(self) -> bool:
        """Ollama 서버 상태 확인"""
        try:
            response = await self.client.get(f"{self.config.host}/api/tags")
            return response.status_code == 200
        except Exception as e:
            logger.error(f"Ollama health check failed: {e}")
            return False

    async def list_models(self) -> List[str]:
        """사용 가능한 모델 목록"""
        try:
            response = await self.client.get(f"{self.config.host}/api/tags")
            data = response.json()
            return [model["name"] for model in data.get("models", [])]
        except Exception as e:
            logger.error(f"Failed to list models: {e}")
            return []

    async def generate(self,
                      prompt: str,
                      stream: bool = True) -> AsyncGenerator[str, None]:
        """텍스트 생성 (스트리밍)"""
        payload = {
            "model": self.config.model,
            "prompt": prompt,
            "temperature": self.config.temperature,
            "options": {
                "num_predict": self.config.max_tokens,
            },
            "stream": stream
        }

        try:
            response = await self.client.post(
                f"{self.config.host}/api/generate",
                json=payload,
                timeout=None  # 스트리밍은 타임아웃 없음
            )

            if stream:
                async for line in response.aiter_lines():
                    if line:
                        data = json.loads(line)
                        if "response" in data:
                            yield data["response"]
            else:
                data = response.json()
                yield data["response"]

        except Exception as e:
            logger.error(f"Generation failed: {e}")
            yield f"Error: {str(e)}"

    async def analyze_context(self, context: Dict[str, Any]) -> AIResponse:
        """터미널 컨텍스트 분석"""
        start_time = datetime.now()

        # 프롬프트 생성
        prompt = self._build_analysis_prompt(context)

        # AI 응답 수집
        response_text = ""
        async for chunk in self.generate(prompt):
            response_text += chunk

        # 응답 파싱
        parsed = self._parse_analysis_response(response_text)

        processing_time = (datetime.now() - start_time).total_seconds()

        return AIResponse(
            content=response_text,
            suggestions=parsed.get("suggestions", []),
            warnings=parsed.get("warnings", []),
            errors=parsed.get("errors", []),
            model=self.config.model,
            timestamp=start_time,
            processing_time=processing_time
        )

    def _build_analysis_prompt(self, context: Dict[str, Any]) -> str:
        """분석 프롬프트 생성"""
        command = context.get("command", "")
        output = context.get("output", "")
        error = context.get("error", "")
        cwd = context.get("cwd", "")
        history = context.get("history", [])

        prompt = f"""You are a helpful terminal assistant. Analyze the following terminal context and provide assistance.

Current Directory: {cwd}
Command: {command}
Output: {output}
Error: {error}

Recent History:
{self._format_history(history)}

Based on this context, provide:
1. Suggestions for what the user might want to do next
2. Warnings about potential issues
3. Error explanations and solutions if applicable

Format your response as JSON with keys: suggestions, warnings, errors
Each should be a list of strings.
"""
        return prompt

    def _format_history(self, history: List[Dict]) -> str:
        """히스토리 포맷팅"""
        if not history:
            return "No recent commands"

        formatted = []
        for cmd in history[-5:]:  # 최근 5개만
            formatted.append(f"- {cmd.get('command', '')} (exit: {cmd.get('exit_code', 'N/A')})")

        return "\n".join(formatted)

    def _parse_analysis_response(self, response: str) -> Dict[str, List[str]]:
        """AI 응답 파싱"""
        # JSON 추출 시도
        try:
            # JSON 블록 찾기
            start = response.find("{")
            end = response.rfind("}") + 1

            if start >= 0 and end > start:
                json_str = response[start:end]
                return json.loads(json_str)
        except:
            pass

        # 휴리스틱 파싱
        result = {
            "suggestions": [],
            "warnings": [],
            "errors": []
        }

        lines = response.split("\n")
        current_section = None

        for line in lines:
            line = line.strip()

            if "suggestion" in line.lower():
                current_section = "suggestions"
            elif "warning" in line.lower():
                current_section = "warnings"
            elif "error" in line.lower():
                current_section = "errors"
            elif line.startswith("-") or line.startswith("*"):
                if current_section:
                    result[current_section].append(line[1:].strip())

        return result

    async def close(self):
        """클라이언트 종료"""
        await self.client.aclose()
```

## Step 2: 프롬프트 템플릿 시스템

### ai/prompts.py
```python
from typing import Dict, Any, List
from enum import Enum


class PromptType(Enum):
    """프롬프트 타입"""
    COMMAND_ANALYSIS = "command_analysis"
    ERROR_DIAGNOSIS = "error_diagnosis"
    SUGGESTION = "suggestion"
    CODE_COMPLETION = "code_completion"
    DOCUMENTATION = "documentation"


class PromptTemplate:
    """프롬프트 템플릿 관리"""

    templates = {
        PromptType.COMMAND_ANALYSIS: """As a terminal assistant, analyze this command execution:

Command: {command}
Exit Code: {exit_code}
Output: {output}
Working Directory: {cwd}

Provide:
1. What the command did
2. Any potential issues
3. Suggested next steps

Be concise and helpful.""",

        PromptType.ERROR_DIAGNOSIS: """Diagnose this terminal error:

Command: {command}
Error Output: {error}
Exit Code: {exit_code}

Provide:
1. What went wrong
2. How to fix it
3. Alternative approaches

Focus on practical solutions.""",

        PromptType.SUGGESTION: """Based on the recent terminal activity:

Recent Commands:
{history}

Current Directory: {cwd}
Last Command: {last_command}

Suggest the most likely next commands the user might want to run.
Provide 3-5 suggestions with brief explanations.""",

        PromptType.CODE_COMPLETION: """Complete this command:

Partial Command: {partial}
Context: {context}

Provide the most likely completions.""",

        PromptType.DOCUMENTATION: """Provide documentation for:

Command: {command}

Include:
1. Brief description
2. Common usage examples
3. Important flags/options
4. Related commands"""
    }

    @classmethod
    def get_prompt(cls, prompt_type: PromptType, **kwargs) -> str:
        """프롬프트 생성"""
        template = cls.templates.get(prompt_type, "")
        return template.format(**kwargs)

    @classmethod
    def create_context_prompt(cls, context: Dict[str, Any]) -> str:
        """컨텍스트 기반 프롬프트 자동 선택"""
        exit_code = context.get("exit_code", 0)
        error = context.get("error", "")

        # 에러가 있으면 에러 진단
        if exit_code != 0 or error:
            return cls.get_prompt(
                PromptType.ERROR_DIAGNOSIS,
                command=context.get("command", ""),
                error=error,
                exit_code=exit_code
            )

        # 일반 명령어 분석
        return cls.get_prompt(
            PromptType.COMMAND_ANALYSIS,
            command=context.get("command", ""),
            exit_code=exit_code,
            output=context.get("output", "")[:500],  # 출력 제한
            cwd=context.get("cwd", "")
        )
```

## Step 3: AI 트리거 시스템

### ai/triggers.py
```python
import re
from typing import Dict, Any, List, Optional
from dataclasses import dataclass
from enum import Enum


class TriggerType(Enum):
    """트리거 타입"""
    ERROR = "error"
    PATTERN = "pattern"
    KEYWORD = "keyword"
    MANUAL = "manual"
    PERIODIC = "periodic"


@dataclass
class Trigger:
    """AI 트리거"""
    type: TriggerType
    pattern: Optional[str] = None
    priority: int = 5
    description: str = ""

    def matches(self, context: Dict[str, Any]) -> bool:
        """트리거 매칭 확인"""
        if self.type == TriggerType.ERROR:
            return context.get("exit_code", 0) != 0

        elif self.type == TriggerType.PATTERN and self.pattern:
            command = context.get("command", "")
            output = context.get("output", "")
            return bool(re.search(self.pattern, command + output))

        elif self.type == TriggerType.KEYWORD and self.pattern:
            command = context.get("command", "").lower()
            return self.pattern.lower() in command

        return False


class TriggerManager:
    """AI 트리거 관리"""

    def __init__(self):
        self.triggers = self._init_default_triggers()
        self.enabled = True

    def _init_default_triggers(self) -> List[Trigger]:
        """기본 트리거 설정"""
        return [
            # 에러 트리거
            Trigger(
                type=TriggerType.ERROR,
                priority=10,
                description="명령어 실행 실패"
            ),

            # 위험 명령어 패턴
            Trigger(
                type=TriggerType.PATTERN,
                pattern=r"rm\s+-rf\s+/|sudo\s+rm\s+-rf",
                priority=10,
                description="위험한 삭제 명령어"
            ),

            # Git 에러
            Trigger(
                type=TriggerType.PATTERN,
                pattern=r"fatal:|error:|rejected|conflict",
                priority=8,
                description="Git 에러"
            ),

            # 권한 에러
            Trigger(
                type=TriggerType.PATTERN,
                pattern=r"permission denied|access denied|unauthorized",
                priority=8,
                description="권한 에러"
            ),

            # 도움 요청
            Trigger(
                type=TriggerType.KEYWORD,
                pattern="help",
                priority=5,
                description="도움말 요청"
            ),

            # 설치 명령어
            Trigger(
                type=TriggerType.PATTERN,
                pattern=r"uv add|npm install|apt install|brew install",
                priority=3,
                description="패키지 설치"
            ),
        ]

    def should_trigger(self, context: Dict[str, Any]) -> Optional[Trigger]:
        """트리거 확인"""
        if not self.enabled:
            return None

        # 매칭되는 트리거 찾기
        matched_triggers = [
            trigger for trigger in self.triggers
            if trigger.matches(context)
        ]

        if not matched_triggers:
            return None

        # 우선순위가 가장 높은 트리거 반환
        return max(matched_triggers, key=lambda t: t.priority)

    def add_trigger(self, trigger: Trigger):
        """트리거 추가"""
        self.triggers.append(trigger)

    def remove_trigger(self, description: str):
        """트리거 제거"""
        self.triggers = [
            t for t in self.triggers
            if t.description != description
        ]

    def set_enabled(self, enabled: bool):
        """트리거 활성화/비활성화"""
        self.enabled = enabled
```

## Step 4: 통합 테스트

### test_ollama.py
```python
#!/usr/bin/env python3
import asyncio
import json
from ai.ollama_client import OllamaClient, OllamaConfig
from ai.prompts import PromptTemplate, PromptType
from ai.triggers import TriggerManager


async def test_ollama_connection():
    """Ollama 연결 테스트"""
    print("=== Ollama 연결 테스트 ===\n")

    client = OllamaClient()

    # 상태 확인
    is_healthy = await client.check_health()
    print(f"Ollama 서버 상태: {'정상' if is_healthy else '오류'}")

    if not is_healthy:
        print("Ollama 서버가 실행중이 아닙니다. 'ollama serve'를 실행하세요.")
        return False

    # 모델 목록
    models = await client.list_models()
    print(f"사용 가능한 모델: {models}")

    return True


async def test_generation():
    """텍스트 생성 테스트"""
    print("\n=== 텍스트 생성 테스트 ===\n")

    client = OllamaClient()

    prompt = "Write a simple Python hello world function"
    print(f"프롬프트: {prompt}")
    print("응답: ", end="", flush=True)

    async for chunk in client.generate(prompt):
        print(chunk, end="", flush=True)

    print("\n")


async def test_context_analysis():
    """컨텍스트 분석 테스트"""
    print("\n=== 컨텍스트 분석 테스트 ===\n")

    client = OllamaClient()

    # 테스트 컨텍스트
    context = {
        "command": "git push origin main",
        "output": "",
        "error": "error: failed to push some refs to 'origin'\nhint: Updates were rejected because the remote contains work that you do not have locally.",
        "exit_code": 1,
        "cwd": "/home/user/project",
        "history": [
            {"command": "git add .", "exit_code": 0},
            {"command": "git commit -m 'Update'", "exit_code": 0}
        ]
    }

    print("분석 중...")
    response = await client.analyze_context(context)

    print(f"\n모델: {response.model}")
    print(f"처리 시간: {response.processing_time:.2f}초")

    print("\n제안사항:")
    for suggestion in response.suggestions:
        print(f"  - {suggestion}")

    print("\n경고:")
    for warning in response.warnings:
        print(f"  - {warning}")

    print("\n에러 해결:")
    for error in response.errors:
        print(f"  - {error}")


def test_triggers():
    """트리거 시스템 테스트"""
    print("\n=== 트리거 시스템 테스트 ===\n")

    manager = TriggerManager()

    # 테스트 케이스
    test_cases = [
        {
            "name": "에러 트리거",
            "context": {"command": "ls /nonexistent", "exit_code": 1}
        },
        {
            "name": "위험 명령어",
            "context": {"command": "sudo rm -rf /", "exit_code": 0}
        },
        {
            "name": "Git 에러",
            "context": {"command": "git push", "output": "fatal: not a git repository"}
        },
        {
            "name": "일반 명령어",
            "context": {"command": "ls -la", "exit_code": 0}
        }
    ]

    for test in test_cases:
        trigger = manager.should_trigger(test["context"])
        print(f"{test['name']}: ", end="")

        if trigger:
            print(f"트리거됨 - {trigger.description} (우선순위: {trigger.priority})")
        else:
            print("트리거 없음")


async def main():
    """메인 테스트 함수"""
    # Ollama 연결 확인
    if not await test_ollama_connection():
        return

    # 각 기능 테스트
    await test_generation()
    await test_context_analysis()
    test_triggers()

    print("\n모든 테스트 완료!")


if __name__ == "__main__":
    asyncio.run(main())
```

## Checkpoint 3: Ollama 통합 테스트

### 실행 방법
```bash
# Ollama 서버 시작 (별도 터미널)
ollama serve

# 테스트 실행
python test_ollama.py
```

### 체크리스트
- [ ] Ollama 서버 연결 성공
- [ ] 모델 목록 조회 가능
- [ ] 텍스트 생성 스트리밍 작동
- [ ] 컨텍스트 분석 응답 파싱
- [ ] 트리거 시스템 정상 작동
- [ ] 에러 처리 및 타임아웃 처리
- [ ] 비동기 처리 정상 작동

### 예상 출력
```
=== Ollama 연결 테스트 ===

Ollama 서버 상태: 정상
사용 가능한 모델: ['codellama:7b', 'mistral:7b']

=== 텍스트 생성 테스트 ===

프롬프트: Write a simple Python hello world function
응답: def hello_world():
    print("Hello, World!")

=== 컨텍스트 분석 테스트 ===

분석 중...

모델: codellama:7b
처리 시간: 2.34초

제안사항:
  - Run 'git pull origin main' to fetch remote changes
  - Use 'git push --force' if you're sure about overwriting

경고:
  - Remote repository has changes not in your local branch

에러 해결:
  - Pull remote changes before pushing
```

## 문제 해결

### 1. Ollama 연결 실패
```bash
# Ollama 상태 확인
curl http://localhost:11434/api/tags

# 포트 확인
lsof -i :11434

# Ollama 재시작
ollama serve
```

### 2. 모델 없음
```bash
# 모델 다운로드
ollama pull codellama:7b
ollama pull mistral:7b
```

### 3. 느린 응답
```python
# 더 작은 모델 사용
config = OllamaConfig(model="mistral:7b")

# 토큰 수 제한
config.max_tokens = 200
```

## 다음 단계

Ollama 통합이 완료되면 [05-context-management.md](05-context-management.md)로 진행하여 스마트 컨텍스트 시스템을 구현합니다.
