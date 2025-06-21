# 06. 실시간 기능 구현

## 목표
터미널 작업을 방해하지 않으면서 실시간으로 AI 분석과 도움을 제공하는 비동기 시스템을 구현합니다.

## 핵심 설계 원칙

### 1. 논블로킹 아키텍처
- 모든 AI 처리는 백그라운드에서
- 터미널 입출력 우선순위 최상위
- UI 업데이트는 별도 스레드

### 2. 스마트 트리거링
- 필요한 순간에만 AI 활성화
- 우선순위 기반 처리
- 중복 분석 방지

## Step 1: 비동기 이벤트 시스템

### utils/events.py
```python
import asyncio
from typing import Dict, Any, Callable, List, Optional
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum, auto
import logging
from queue import PriorityQueue
import threading

logger = logging.getLogger(__name__)


class EventType(Enum):
    """이벤트 타입"""
    COMMAND_START = auto()
    COMMAND_END = auto()
    ERROR_DETECTED = auto()
    AI_ANALYSIS_REQUEST = auto()
    AI_ANALYSIS_COMPLETE = auto()
    CONTEXT_UPDATE = auto()
    UI_UPDATE = auto()
    USER_INPUT = auto()


@dataclass(order=True)
class Event:
    """우선순위 이벤트"""
    priority: int
    type: EventType = field(compare=False)
    data: Dict[str, Any] = field(compare=False)
    timestamp: datetime = field(default_factory=datetime.now, compare=False)
    callback: Optional[Callable] = field(default=None, compare=False)


class EventBus:
    """비동기 이벤트 버스"""
    
    def __init__(self):
        self.listeners: Dict[EventType, List[Callable]] = {}
        self.event_queue = asyncio.Queue()
        self.priority_queue = PriorityQueue()
        self.running = False
        self._lock = threading.Lock()
        
    def subscribe(self, event_type: EventType, handler: Callable):
        """이벤트 구독"""
        with self._lock:
            if event_type not in self.listeners:
                self.listeners[event_type] = []
            self.listeners[event_type].append(handler)
            
    def unsubscribe(self, event_type: EventType, handler: Callable):
        """구독 해제"""
        with self._lock:
            if event_type in self.listeners:
                self.listeners[event_type].remove(handler)
                
    async def emit(self, event: Event):
        """이벤트 발행"""
        await self.event_queue.put(event)
        
    def emit_sync(self, event: Event):
        """동기 이벤트 발행 (스레드 안전)"""
        self.priority_queue.put((event.priority, event))
        
    async def start(self):
        """이벤트 루프 시작"""
        self.running = True
        
        # 비동기 큐 처리
        asyncio.create_task(self._process_async_queue())
        
        # 우선순위 큐 처리
        asyncio.create_task(self._process_priority_queue())
        
    async def stop(self):
        """이벤트 루프 중지"""
        self.running = False
        
    async def _process_async_queue(self):
        """비동기 큐 처리"""
        while self.running:
            try:
                event = await asyncio.wait_for(
                    self.event_queue.get(), 
                    timeout=0.1
                )
                await self._handle_event(event)
            except asyncio.TimeoutError:
                continue
            except Exception as e:
                logger.error(f"Event processing error: {e}")
                
    async def _process_priority_queue(self):
        """우선순위 큐 처리"""
        while self.running:
            try:
                if not self.priority_queue.empty():
                    _, event = self.priority_queue.get(timeout=0.1)
                    await self._handle_event(event)
                else:
                    await asyncio.sleep(0.1)
            except Exception as e:
                logger.error(f"Priority queue error: {e}")
                
    async def _handle_event(self, event: Event):
        """이벤트 처리"""
        with self._lock:
            handlers = self.listeners.get(event.type, [])
            
        for handler in handlers:
            try:
                if asyncio.iscoroutinefunction(handler):
                    await handler(event)
                else:
                    handler(event)
            except Exception as e:
                logger.error(f"Handler error for {event.type}: {e}")
                
        # 콜백 실행
        if event.callback:
            try:
                if asyncio.iscoroutinefunction(event.callback):
                    await event.callback(event)
                else:
                    event.callback(event)
            except Exception as e:
                logger.error(f"Callback error: {e}")
```

## Step 2: 실시간 분석 파이프라인

### ai/realtime_analyzer.py
```python
import asyncio
from typing import Dict, Any, Optional, List
from datetime import datetime, timedelta
import logging
from dataclasses import dataclass
from collections import deque

from .ollama_client import OllamaClient, AIResponse
from .context_manager import ContextManager
from ..utils.events import EventBus, Event, EventType

logger = logging.getLogger(__name__)


@dataclass
class AnalysisRequest:
    """분석 요청"""
    id: str
    context: Dict[str, Any]
    trigger_type: str
    priority: int
    timestamp: datetime
    retry_count: int = 0


class RealtimeAnalyzer:
    """실시간 AI 분석기"""
    
    def __init__(self,
                 ollama_client: OllamaClient,
                 context_manager: ContextManager,
                 event_bus: EventBus):
        self.ollama_client = ollama_client
        self.context_manager = context_manager
        self.event_bus = event_bus
        
        # 분석 큐
        self.analysis_queue: asyncio.Queue[AnalysisRequest] = asyncio.Queue()
        self.active_analyses: Dict[str, AnalysisRequest] = {}
        
        # 성능 제한
        self.max_concurrent = 2
        self.min_interval = timedelta(seconds=2)
        self.last_analysis_time = datetime.now()
        
        # 캐시
        self.response_cache: Dict[str, AIResponse] = {}
        self.cache_size = 50
        
        # 이벤트 구독
        self._subscribe_events()
        
    def _subscribe_events(self):
        """이벤트 구독"""
        self.event_bus.subscribe(
            EventType.AI_ANALYSIS_REQUEST,
            self._handle_analysis_request
        )
        
    async def start(self):
        """분석기 시작"""
        # 워커 시작
        for i in range(self.max_concurrent):
            asyncio.create_task(self._analysis_worker(i))
            
        logger.info("Realtime analyzer started")
        
    async def _analysis_worker(self, worker_id: int):
        """분석 워커"""
        logger.info(f"Analysis worker {worker_id} started")
        
        while True:
            try:
                # 최소 간격 유지
                time_since_last = datetime.now() - self.last_analysis_time
                if time_since_last < self.min_interval:
                    await asyncio.sleep(
                        (self.min_interval - time_since_last).total_seconds()
                    )
                    
                # 요청 가져오기
                request = await self.analysis_queue.get()
                
                # 캐시 확인
                cache_key = self._get_cache_key(request.context)
                if cache_key in self.response_cache:
                    logger.info(f"Using cached response for {request.id}")
                    response = self.response_cache[cache_key]
                else:
                    # AI 분석 실행
                    response = await self._perform_analysis(request)
                    
                    # 캐시 저장
                    self._update_cache(cache_key, response)
                    
                # 결과 이벤트 발행
                await self.event_bus.emit(Event(
                    priority=5,
                    type=EventType.AI_ANALYSIS_COMPLETE,
                    data={
                        "request_id": request.id,
                        "response": response,
                        "context": request.context
                    }
                ))
                
                self.last_analysis_time = datetime.now()
                
            except Exception as e:
                logger.error(f"Worker {worker_id} error: {e}")
                
                # 재시도 로직
                if request and request.retry_count < 3:
                    request.retry_count += 1
                    await self.analysis_queue.put(request)
                    
    async def _perform_analysis(self, request: AnalysisRequest) -> AIResponse:
        """AI 분석 수행"""
        logger.info(f"Performing analysis for {request.id}")
        
        # 컨텍스트 준비
        filtered_context = self.context_manager.get_filtered_context()
        
        # AI 호출
        response = await self.ollama_client.analyze_context(filtered_context)
        
        return response
        
    async def _handle_analysis_request(self, event: Event):
        """분석 요청 처리"""
        data = event.data
        
        # 중복 확인
        request_id = data.get("id", f"req_{datetime.now().timestamp()}")
        if request_id in self.active_analyses:
            logger.debug(f"Duplicate request ignored: {request_id}")
            return
            
        # 요청 생성
        request = AnalysisRequest(
            id=request_id,
            context=data.get("context", {}),
            trigger_type=data.get("trigger_type", "manual"),
            priority=data.get("priority", 5),
            timestamp=datetime.now()
        )
        
        # 큐에 추가
        self.active_analyses[request_id] = request
        await self.analysis_queue.put(request)
        
    def _get_cache_key(self, context: Dict[str, Any]) -> str:
        """캐시 키 생성"""
        # 최근 명령어 기반 키 생성
        commands = context.get("commands", [])[-5:]
        key_parts = [cmd.get("command", "") for cmd in commands]
        return ":".join(key_parts)
        
    def _update_cache(self, key: str, response: AIResponse):
        """캐시 업데이트"""
        # 크기 제한
        if len(self.response_cache) >= self.cache_size:
            # 가장 오래된 항목 제거
            oldest = min(
                self.response_cache.items(),
                key=lambda x: x[1].timestamp
            )
            del self.response_cache[oldest[0]]
            
        self.response_cache[key] = response
```

## Step 3: UI 업데이트 시스템

### ui/realtime_updates.py
```python
from textual.message import Message
from textual.reactive import reactive
from typing import Dict, Any, List, Optional
import asyncio
from datetime import datetime

from ..utils.events import EventBus, Event, EventType
from ..ai.ollama_client import AIResponse


class AIUpdateMessage(Message):
    """AI 업데이트 메시지"""
    
    def __init__(self, response: AIResponse, context: Dict[str, Any]):
        super().__init__()
        self.response = response
        self.context = context


class RealtimeUIUpdater:
    """실시간 UI 업데이트 관리"""
    
    def __init__(self, app, event_bus: EventBus):
        self.app = app
        self.event_bus = event_bus
        
        # 업데이트 큐
        self.update_queue = asyncio.Queue()
        
        # 업데이트 제한
        self.max_updates_per_second = 5
        self.last_update_time = datetime.now()
        
        # 이벤트 구독
        self._subscribe_events()
        
    def _subscribe_events(self):
        """이벤트 구독"""
        self.event_bus.subscribe(
            EventType.AI_ANALYSIS_COMPLETE,
            self._handle_ai_complete
        )
        self.event_bus.subscribe(
            EventType.CONTEXT_UPDATE,
            self._handle_context_update
        )
        
    async def start(self):
        """업데이터 시작"""
        asyncio.create_task(self._update_loop())
        
    async def _update_loop(self):
        """UI 업데이트 루프"""
        while True:
            try:
                # 업데이트 가져오기
                update = await self.update_queue.get()
                
                # 속도 제한
                await self._rate_limit()
                
                # UI 업데이트
                await self._apply_update(update)
                
            except Exception as e:
                logger.error(f"UI update error: {e}")
                
    async def _rate_limit(self):
        """업데이트 속도 제한"""
        time_since_last = (datetime.now() - self.last_update_time).total_seconds()
        min_interval = 1.0 / self.max_updates_per_second
        
        if time_since_last < min_interval:
            await asyncio.sleep(min_interval - time_since_last)
            
        self.last_update_time = datetime.now()
        
    async def _apply_update(self, update: Dict[str, Any]):
        """UI 업데이트 적용"""
        update_type = update.get("type")
        
        if update_type == "ai_response":
            # AI 사이드바 업데이트
            self.app.call_from_thread(
                self._update_ai_sidebar,
                update["response"],
                update["context"]
            )
        elif update_type == "status":
            # 상태 표시 업데이트
            self.app.call_from_thread(
                self._update_status,
                update["message"]
            )
            
    def _update_ai_sidebar(self, response: AIResponse, context: Dict[str, Any]):
        """AI 사이드바 업데이트"""
        sidebar = self.app.query_one("AISidebar")
        
        # 제안사항 추가
        for suggestion in response.suggestions:
            sidebar.add_message(suggestion, "suggestion")
            
        # 경고 추가
        for warning in response.warnings:
            sidebar.add_message(warning, "warning")
            
        # 에러 해결책 추가
        for error in response.errors:
            sidebar.add_message(error, "error")
            
    def _update_status(self, message: str):
        """상태 메시지 업데이트"""
        status_bar = self.app.query_one("#status-bar")
        status_bar.update(message)
        
    async def _handle_ai_complete(self, event: Event):
        """AI 분석 완료 처리"""
        await self.update_queue.put({
            "type": "ai_response",
            "response": event.data["response"],
            "context": event.data["context"]
        })
        
    async def _handle_context_update(self, event: Event):
        """컨텍스트 업데이트 처리"""
        # 상태 메시지만 표시
        message = event.data.get("message", "Context updated")
        await self.update_queue.put({
            "type": "status",
            "message": message
        })
```

## Step 4: 통합 실시간 시스템

### main_realtime.py
```python
#!/usr/bin/env python3
import asyncio
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))

from ui.app import TerminalAIApp
from terminal.manager import TerminalManager
from ai.ollama_client import OllamaClient, OllamaConfig
from ai.context_manager import ContextManager
from ai.realtime_analyzer import RealtimeAnalyzer
from ui.realtime_updates import RealtimeUIUpdater
from utils.events import EventBus, Event, EventType
from utils.config import load_config


class RealtimeTerminalAI(TerminalAIApp):
    """실시간 기능이 통합된 터미널 AI"""
    
    def __init__(self):
        super().__init__()
        
        # 컴포넌트 초기화
        self.event_bus = EventBus()
        self.terminal_manager = TerminalManager()
        self.ollama_client = OllamaClient(OllamaConfig())
        self.context_manager = ContextManager(self.terminal_manager)
        
        # 실시간 컴포넌트
        self.realtime_analyzer = RealtimeAnalyzer(
            self.ollama_client,
            self.context_manager,
            self.event_bus
        )
        self.ui_updater = RealtimeUIUpdater(self, self.event_bus)
        
        # 이벤트 연결
        self._setup_event_handlers()
        
    def _setup_event_handlers(self):
        """이벤트 핸들러 설정"""
        # 터미널 이벤트를 이벤트 버스로 전달
        original_on_command_end = self.terminal_manager.on_command_end
        
        def enhanced_on_command_end(command: str, exit_code: int):
            # 원래 핸들러 호출
            if original_on_command_end:
                original_on_command_end(command, exit_code)
                
            # 이벤트 발행
            self.event_bus.emit_sync(Event(
                priority=7,
                type=EventType.COMMAND_END,
                data={
                    "command": command,
                    "exit_code": exit_code,
                    "timestamp": datetime.now()
                }
            ))
            
            # 에러인 경우 AI 분석 요청
            if exit_code != 0:
                self.event_bus.emit_sync(Event(
                    priority=9,
                    type=EventType.AI_ANALYSIS_REQUEST,
                    data={
                        "trigger_type": "error",
                        "context": self.context_manager.get_filtered_context()
                    }
                ))
                
        self.terminal_manager.on_command_end = enhanced_on_command_end
        
    async def on_mount(self):
        """앱 마운트 시 초기화"""
        await super().on_mount()
        
        # 이벤트 버스 시작
        await self.event_bus.start()
        
        # 실시간 컴포넌트 시작
        await self.realtime_analyzer.start()
        await self.ui_updater.start()
        
        # 초기 상태 확인
        if await self.ollama_client.check_health():
            self.notify("AI Assistant ready", severity="information")
        else:
            self.notify("Ollama not available", severity="warning")
            
    async def on_unmount(self):
        """앱 종료 시 정리"""
        await self.event_bus.stop()
        await super().on_unmount()


async def main():
    """메인 실행 함수"""
    app = RealtimeTerminalAI()
    await app.run_async()


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\nApplication terminated")
        sys.exit(0)
```

## Checkpoint 4: 실시간 통합 테스트

### 실행 방법
```bash
# Ollama 서버 시작
ollama serve

# 실시간 앱 실행
python main_realtime.py
```

### 테스트 시나리오
1. **에러 트리거 테스트**
   ```bash
   # 존재하지 않는 파일
   cat /nonexistent/file.txt
   # AI가 자동으로 에러 분석
   ```

2. **Git 작업 테스트**
   ```bash
   git add .
   git commit -m "test"
   git push origin nonexistent-branch
   # AI가 Git 에러 해결책 제시
   ```

3. **성능 테스트**
   ```bash
   # 연속 명령어 실행
   for i in {1..10}; do echo "Test $i"; done
   # UI가 블로킹되지 않는지 확인
   ```

### 체크리스트
- [ ] 터미널 작업 중 UI 반응성 유지
- [ ] 에러 발생 시 자동 AI 분석
- [ ] AI 응답이 사이드바에 실시간 표시
- [ ] 여러 분석이 동시에 처리됨
- [ ] 캐시가 정상 작동함
- [ ] 메모리 사용량이 안정적
- [ ] Ctrl+A로 AI 토글 가능

### 예상 동작
```
Terminal                          AI Assistant
--------                          ------------
$ ls /invalid                     🟡 Processing...
ls: /invalid: No such file        
                                 [ERROR] 12:34:56
                                 Directory not found
                                 
                                 Try:
                                 - Check spelling
                                 - Use 'ls' to see available dirs
                                 - Use 'mkdir' to create

$ git push                       🟡 Processing...
fatal: not a git repository      
                                 [ERROR] 12:35:01
                                 Not in a git repository
                                 
                                 Initialize with:
                                 git init
                                 git remote add origin <url>
```

## 문제 해결

### 1. UI 업데이트 지연
```python
# 업데이트 배치 처리
updates = []
while not update_queue.empty() and len(updates) < 5:
    updates.append(update_queue.get_nowait())
    
# 한 번에 적용
for update in updates:
    apply_update(update)
```

### 2. 메모리 누수
```python
# 이벤트 리스너 정리
def cleanup():
    for event_type, handlers in listeners.items():
        handlers.clear()
        
# 오래된 캐시 주기적 정리
async def cleanup_cache():
    while True:
        await asyncio.sleep(300)  # 5분마다
        # 오래된 항목 제거
```

### 3. AI 응답 속도
```python
# 프리페칭
if likely_next_command:
    asyncio.create_task(
        prefetch_analysis(likely_next_command)
    )
    
# 부분 응답 스트리밍
async for chunk in ollama_client.stream_generate(prompt):
    ui.append_chunk(chunk)
```

## 다음 단계

실시간 기능이 구현되면 [07-optimization.md](07-optimization.md)로 진행하여 성능을 최적화합니다.