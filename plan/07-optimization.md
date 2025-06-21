# 07. 성능 최적화

## 목표
실시간 터미널 AI 어시스턴트의 성능을 최적화하여 빠른 응답성과 낮은 리소스 사용을 달성합니다.

## 성능 병목 지점

### 1. AI 응답 지연
- Ollama 모델 추론 시간
- 네트워크 레이턴시
- 컨텍스트 크기

### 2. 메모리 사용
- 명령어 히스토리 누적
- AI 응답 캐시
- 터미널 출력 버퍼

### 3. CPU 사용
- ANSI 파싱
- 이벤트 처리
- UI 렌더링

## Step 1: 프로파일링 도구

### utils/profiler.py
```python
import time
import psutil
import asyncio
from typing import Dict, Any, Callable, Optional
from dataclasses import dataclass, field
from datetime import datetime
import functools
import logging
from contextlib import contextmanager
import cProfile
import pstats
import io

logger = logging.getLogger(__name__)


@dataclass
class PerformanceMetrics:
    """성능 메트릭"""
    function_name: str
    call_count: int = 0
    total_time: float = 0.0
    avg_time: float = 0.0
    max_time: float = 0.0
    min_time: float = float('inf')
    
    def update(self, duration: float):
        """메트릭 업데이트"""
        self.call_count += 1
        self.total_time += duration
        self.avg_time = self.total_time / self.call_count
        self.max_time = max(self.max_time, duration)
        self.min_time = min(self.min_time, duration)


class PerformanceProfiler:
    """성능 프로파일러"""
    
    def __init__(self):
        self.metrics: Dict[str, PerformanceMetrics] = {}
        self.enabled = True
        
        # 시스템 리소스 모니터링
        self.process = psutil.Process()
        self.start_time = datetime.now()
        
    def measure(self, name: Optional[str] = None):
        """함수 실행 시간 측정 데코레이터"""
        def decorator(func):
            func_name = name or f"{func.__module__}.{func.__name__}"
            
            @functools.wraps(func)
            def sync_wrapper(*args, **kwargs):
                if not self.enabled:
                    return func(*args, **kwargs)
                    
                start = time.perf_counter()
                try:
                    result = func(*args, **kwargs)
                    return result
                finally:
                    duration = time.perf_counter() - start
                    self._update_metrics(func_name, duration)
                    
            @functools.wraps(func)
            async def async_wrapper(*args, **kwargs):
                if not self.enabled:
                    return await func(*args, **kwargs)
                    
                start = time.perf_counter()
                try:
                    result = await func(*args, **kwargs)
                    return result
                finally:
                    duration = time.perf_counter() - start
                    self._update_metrics(func_name, duration)
                    
            return async_wrapper if asyncio.iscoroutinefunction(func) else sync_wrapper
            
        return decorator
        
    def _update_metrics(self, func_name: str, duration: float):
        """메트릭 업데이트"""
        if func_name not in self.metrics:
            self.metrics[func_name] = PerformanceMetrics(func_name)
            
        self.metrics[func_name].update(duration)
        
        # 느린 함수 경고
        if duration > 1.0:
            logger.warning(f"Slow function: {func_name} took {duration:.2f}s")
            
    @contextmanager
    def profile_block(self, name: str):
        """코드 블록 프로파일링"""
        start = time.perf_counter()
        try:
            yield
        finally:
            duration = time.perf_counter() - start
            self._update_metrics(f"block.{name}", duration)
            
    def get_resource_usage(self) -> Dict[str, Any]:
        """현재 리소스 사용량"""
        return {
            "cpu_percent": self.process.cpu_percent(interval=0.1),
            "memory_mb": self.process.memory_info().rss / 1024 / 1024,
            "threads": self.process.num_threads(),
            "open_files": len(self.process.open_files()),
            "uptime": (datetime.now() - self.start_time).total_seconds()
        }
        
    def get_report(self) -> str:
        """성능 리포트 생성"""
        report = ["=== Performance Report ===\n"]
        
        # 리소스 사용량
        resources = self.get_resource_usage()
        report.append("Resource Usage:")
        report.append(f"  CPU: {resources['cpu_percent']:.1f}%")
        report.append(f"  Memory: {resources['memory_mb']:.1f} MB")
        report.append(f"  Threads: {resources['threads']}")
        report.append(f"  Uptime: {resources['uptime']:.1f}s\n")
        
        # 함수 메트릭
        report.append("Function Metrics (sorted by total time):")
        sorted_metrics = sorted(
            self.metrics.values(),
            key=lambda x: x.total_time,
            reverse=True
        )
        
        for metric in sorted_metrics[:20]:  # 상위 20개
            report.append(
                f"  {metric.function_name}: "
                f"calls={metric.call_count}, "
                f"total={metric.total_time:.3f}s, "
                f"avg={metric.avg_time:.3f}s"
            )
            
        return "\n".join(report)
        
    @staticmethod
    def profile_function(func: Callable) -> str:
        """상세 함수 프로파일링"""
        profiler = cProfile.Profile()
        profiler.enable()
        
        func()
        
        profiler.disable()
        
        # 결과 문자열로 변환
        s = io.StringIO()
        ps = pstats.Stats(profiler, stream=s).sort_stats('cumulative')
        ps.print_stats(20)  # 상위 20개
        
        return s.getvalue()


# 전역 프로파일러 인스턴스
profiler = PerformanceProfiler()
```

## Step 2: 메모리 최적화

### utils/memory_optimizer.py
```python
import gc
import weakref
from typing import Any, Dict, List, Optional
from collections import OrderedDict
import sys
from datetime import datetime, timedelta
import logging

logger = logging.getLogger(__name__)


class LRUCache:
    """크기 제한이 있는 LRU 캐시"""
    
    def __init__(self, max_size: int = 100):
        self.cache = OrderedDict()
        self.max_size = max_size
        
    def get(self, key: str) -> Optional[Any]:
        """값 가져오기"""
        if key in self.cache:
            # 최근 사용으로 이동
            self.cache.move_to_end(key)
            return self.cache[key]
        return None
        
    def put(self, key: str, value: Any):
        """값 저장"""
        if key in self.cache:
            self.cache.move_to_end(key)
        else:
            if len(self.cache) >= self.max_size:
                # 가장 오래된 항목 제거
                self.cache.popitem(last=False)
                
        self.cache[key] = value
        
    def clear(self):
        """캐시 초기화"""
        self.cache.clear()
        
    def size(self) -> int:
        """현재 크기"""
        return len(self.cache)


class ObjectPool:
    """객체 재사용 풀"""
    
    def __init__(self, factory: Callable, max_size: int = 50):
        self.factory = factory
        self.pool: List[Any] = []
        self.max_size = max_size
        
    def acquire(self) -> Any:
        """객체 획득"""
        if self.pool:
            return self.pool.pop()
        return self.factory()
        
    def release(self, obj: Any):
        """객체 반환"""
        if len(self.pool) < self.max_size:
            # 객체 초기화
            if hasattr(obj, 'reset'):
                obj.reset()
            self.pool.append(obj)


class MemoryManager:
    """메모리 관리자"""
    
    def __init__(self):
        self.caches: Dict[str, LRUCache] = {}
        self.pools: Dict[str, ObjectPool] = {}
        self.weak_refs: Dict[str, weakref.ref] = {}
        
        # 자동 정리 설정
        self.cleanup_interval = timedelta(minutes=5)
        self.last_cleanup = datetime.now()
        
    def get_cache(self, name: str, max_size: int = 100) -> LRUCache:
        """캐시 가져오기"""
        if name not in self.caches:
            self.caches[name] = LRUCache(max_size)
        return self.caches[name]
        
    def get_pool(self, name: str, factory: Callable, max_size: int = 50) -> ObjectPool:
        """객체 풀 가져오기"""
        if name not in self.pools:
            self.pools[name] = ObjectPool(factory, max_size)
        return self.pools[name]
        
    def store_weak_ref(self, name: str, obj: Any):
        """약한 참조 저장"""
        self.weak_refs[name] = weakref.ref(obj)
        
    def get_weak_ref(self, name: str) -> Optional[Any]:
        """약한 참조 가져오기"""
        if name in self.weak_refs:
            ref = self.weak_refs[name]
            obj = ref()
            if obj is None:
                # 참조가 삭제됨
                del self.weak_refs[name]
            return obj
        return None
        
    def cleanup(self, force: bool = False):
        """메모리 정리"""
        now = datetime.now()
        
        if not force and now - self.last_cleanup < self.cleanup_interval:
            return
            
        logger.info("Starting memory cleanup")
        
        # 가비지 컬렉션
        before = self._get_memory_usage()
        gc.collect()
        after = self._get_memory_usage()
        
        # 캐시 크기 조정
        for name, cache in self.caches.items():
            if cache.size() > cache.max_size * 0.8:
                # 20% 축소
                new_size = int(cache.max_size * 0.8)
                while cache.size() > new_size:
                    cache.cache.popitem(last=False)
                    
        # 죽은 약한 참조 제거
        dead_refs = [
            name for name, ref in self.weak_refs.items()
            if ref() is None
        ]
        for name in dead_refs:
            del self.weak_refs[name]
            
        self.last_cleanup = now
        
        logger.info(
            f"Memory cleanup complete: {before:.1f}MB -> {after:.1f}MB "
            f"(freed: {before-after:.1f}MB)"
        )
        
    def _get_memory_usage(self) -> float:
        """현재 메모리 사용량 (MB)"""
        import psutil
        process = psutil.Process()
        return process.memory_info().rss / 1024 / 1024
        
    def get_stats(self) -> Dict[str, Any]:
        """메모리 통계"""
        return {
            "memory_mb": self._get_memory_usage(),
            "caches": {
                name: cache.size() 
                for name, cache in self.caches.items()
            },
            "pools": {
                name: len(pool.pool)
                for name, pool in self.pools.items()
            },
            "weak_refs": len(self.weak_refs),
            "gc_stats": gc.get_stats()
        }


# 전역 메모리 관리자
memory_manager = MemoryManager()
```

## Step 3: 비동기 최적화

### utils/async_optimizer.py
```python
import asyncio
from typing import List, Callable, Any, Optional, TypeVar, Coroutine
from concurrent.futures import ThreadPoolExecutor
import functools
import logging

logger = logging.getLogger(__name__)

T = TypeVar('T')


class AsyncBatcher:
    """비동기 작업 배치 처리"""
    
    def __init__(self, 
                 batch_size: int = 10,
                 timeout: float = 0.1):
        self.batch_size = batch_size
        self.timeout = timeout
        self.pending: List[Tuple[Callable, asyncio.Future]] = []
        self.processing = False
        
    async def add(self, coro: Coroutine[Any, Any, T]) -> T:
        """작업 추가"""
        future = asyncio.Future()
        self.pending.append((coro, future))
        
        if not self.processing:
            asyncio.create_task(self._process_batch())
            
        return await future
        
    async def _process_batch(self):
        """배치 처리"""
        self.processing = True
        
        try:
            # 타임아웃 또는 배치 크기까지 대기
            await asyncio.sleep(self.timeout)
            
            # 현재 대기 중인 작업 처리
            batch = self.pending[:self.batch_size]
            self.pending = self.pending[self.batch_size:]
            
            if batch:
                # 병렬 실행
                results = await asyncio.gather(
                    *[coro for coro, _ in batch],
                    return_exceptions=True
                )
                
                # 결과 전달
                for (_, future), result in zip(batch, results):
                    if isinstance(result, Exception):
                        future.set_exception(result)
                    else:
                        future.set_result(result)
                        
        finally:
            self.processing = False
            
            # 남은 작업이 있으면 계속 처리
            if self.pending:
                asyncio.create_task(self._process_batch())


class AsyncThrottler:
    """비동기 작업 속도 제한"""
    
    def __init__(self, rate_limit: int, period: float = 1.0):
        self.rate_limit = rate_limit
        self.period = period
        self.semaphore = asyncio.Semaphore(rate_limit)
        self.reset_task = None
        
    async def __aenter__(self):
        await self.semaphore.acquire()
        
        if self.reset_task is None:
            self.reset_task = asyncio.create_task(self._reset_loop())
            
    async def __aexit__(self, *args):
        pass
        
    async def _reset_loop(self):
        """주기적으로 세마포어 리셋"""
        while True:
            await asyncio.sleep(self.period)
            
            # 세마포어 리셋
            self.semaphore = asyncio.Semaphore(self.rate_limit)


class AsyncCache:
    """비동기 캐시"""
    
    def __init__(self, ttl: float = 300.0):  # 5분
        self.cache: Dict[str, Tuple[Any, float]] = {}
        self.ttl = ttl
        self.locks: Dict[str, asyncio.Lock] = {}
        
    async def get_or_compute(self, 
                           key: str, 
                           compute_func: Callable[[], Coroutine[Any, Any, T]]) -> T:
        """캐시에서 가져오거나 계산"""
        # 캐시 확인
        if key in self.cache:
            value, timestamp = self.cache[key]
            if asyncio.get_event_loop().time() - timestamp < self.ttl:
                return value
                
        # 키별 락 획득
        if key not in self.locks:
            self.locks[key] = asyncio.Lock()
            
        async with self.locks[key]:
            # 다시 확인 (다른 코루틴이 이미 계산했을 수 있음)
            if key in self.cache:
                value, timestamp = self.cache[key]
                if asyncio.get_event_loop().time() - timestamp < self.ttl:
                    return value
                    
            # 계산 수행
            value = await compute_func()
            
            # 캐시 저장
            self.cache[key] = (value, asyncio.get_event_loop().time())
            
            return value
            
    def clear(self):
        """캐시 초기화"""
        self.cache.clear()


def run_in_thread(func: Callable[..., T]) -> Callable[..., Coroutine[Any, Any, T]]:
    """동기 함수를 비동기로 실행"""
    @functools.wraps(func)
    async def wrapper(*args, **kwargs):
        loop = asyncio.get_event_loop()
        
        # 스레드 풀에서 실행
        with ThreadPoolExecutor(max_workers=1) as executor:
            return await loop.run_in_executor(
                executor,
                functools.partial(func, *args, **kwargs)
            )
            
    return wrapper


class AsyncPipeline:
    """비동기 파이프라인"""
    
    def __init__(self):
        self.stages: List[Callable] = []
        
    def add_stage(self, func: Callable) -> 'AsyncPipeline':
        """스테이지 추가"""
        self.stages.append(func)
        return self
        
    async def execute(self, initial_value: Any) -> Any:
        """파이프라인 실행"""
        value = initial_value
        
        for stage in self.stages:
            if asyncio.iscoroutinefunction(stage):
                value = await stage(value)
            else:
                value = stage(value)
                
        return value
```

## Step 4: 최적화된 메인 애플리케이션

### main_optimized.py
```python
#!/usr/bin/env python3
import asyncio
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))

from main_realtime import RealtimeTerminalAI
from utils.profiler import profiler
from utils.memory_optimizer import memory_manager
from utils.async_optimizer import AsyncCache, AsyncThrottler
from utils.config import load_config


class OptimizedTerminalAI(RealtimeTerminalAI):
    """최적화된 터미널 AI"""
    
    def __init__(self):
        super().__init__()
        
        # 최적화 컴포넌트
        self.response_cache = AsyncCache(ttl=300)  # 5분 캐시
        self.api_throttler = AsyncThrottler(rate_limit=5, period=1.0)  # 초당 5회
        
        # 프로파일링 활성화
        profiler.enabled = True
        
        # 메모리 관리 설정
        self._setup_memory_management()
        
    def _setup_memory_management(self):
        """메모리 관리 설정"""
        # 캐시 등록
        self.command_cache = memory_manager.get_cache("commands", max_size=500)
        self.context_cache = memory_manager.get_cache("contexts", max_size=100)
        
        # 주기적 정리
        asyncio.create_task(self._periodic_cleanup())
        
    async def _periodic_cleanup(self):
        """주기적 정리 작업"""
        while True:
            await asyncio.sleep(300)  # 5분마다
            
            # 메모리 정리
            memory_manager.cleanup()
            
            # 성능 리포트
            if profiler.enabled:
                logger.info("\n" + profiler.get_report())
                
    @profiler.measure("terminal_output_processing")
    def _handle_terminal_output(self, data: bytes):
        """최적화된 터미널 출력 처리"""
        # 캐시 확인
        cache_key = hashlib.md5(data).hexdigest()
        cached = self.command_cache.get(cache_key)
        
        if cached:
            return cached
            
        # 처리
        result = super()._handle_terminal_output(data)
        
        # 캐시 저장
        self.command_cache.put(cache_key, result)
        
        return result
        
    async def analyze_with_cache(self, context: Dict[str, Any]) -> AIResponse:
        """캐시를 활용한 AI 분석"""
        # 캐시 키 생성
        cache_key = self._generate_context_key(context)
        
        # 캐시 또는 계산
        return await self.response_cache.get_or_compute(
            cache_key,
            lambda: self._perform_throttled_analysis(context)
        )
        
    async def _perform_throttled_analysis(self, context: Dict[str, Any]) -> AIResponse:
        """속도 제한이 적용된 분석"""
        async with self.api_throttler:
            return await self.ollama_client.analyze_context(context)
            
    def _generate_context_key(self, context: Dict[str, Any]) -> str:
        """컨텍스트 캐시 키 생성"""
        # 주요 필드만 사용
        key_parts = []
        
        if "commands" in context:
            recent_commands = context["commands"][-5:]
            for cmd in recent_commands:
                key_parts.append(cmd.get("command", ""))
                
        return ":".join(key_parts)
        
    async def on_mount(self):
        """최적화된 마운트"""
        await super().on_mount()
        
        # 프리페칭
        asyncio.create_task(self._prefetch_common_responses())
        
    async def _prefetch_common_responses(self):
        """일반적인 응답 프리페칭"""
        common_errors = [
            "command not found",
            "permission denied",
            "no such file or directory"
        ]
        
        for error in common_errors:
            context = {
                "commands": [{
                    "command": "example",
                    "error": error,
                    "exit_code": 1
                }]
            }
            
            # 백그라운드에서 캐시 준비
            asyncio.create_task(self.analyze_with_cache(context))


async def main():
    """메인 실행 함수"""
    # 설정 로드
    config = load_config()
    
    # 최적화 설정
    if config.get("optimization", {}).get("enabled", True):
        app = OptimizedTerminalAI()
    else:
        app = RealtimeTerminalAI()
        
    await app.run_async()


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        # 성능 리포트 출력
        print("\n" + profiler.get_report())
        print("\nMemory stats:", memory_manager.get_stats())
        sys.exit(0)
```

## 성능 테스트

### performance_test.py
```python
#!/usr/bin/env python3
import asyncio
import time
import random
from utils.profiler import profiler


async def stress_test():
    """스트레스 테스트"""
    print("=== Performance Stress Test ===\n")
    
    # 많은 명령어 시뮬레이션
    commands = [
        "ls -la",
        "git status",
        "npm install",
        "python script.py",
        "docker ps",
        "kubectl get pods"
    ]
    
    start_time = time.time()
    tasks = []
    
    # 100개의 동시 명령어
    for i in range(100):
        cmd = random.choice(commands)
        # 시뮬레이션된 명령어 실행
        task = asyncio.create_task(simulate_command(cmd))
        tasks.append(task)
        
    await asyncio.gather(*tasks)
    
    duration = time.time() - start_time
    print(f"\nCompleted 100 commands in {duration:.2f}s")
    print(f"Average: {duration/100:.3f}s per command")


async def simulate_command(cmd: str):
    """명령어 실행 시뮬레이션"""
    # 랜덤 지연
    await asyncio.sleep(random.uniform(0.01, 0.1))
    
    # 에러 시뮬레이션 (20% 확률)
    if random.random() < 0.2:
        return f"Error executing {cmd}"
    return f"Success: {cmd}"


if __name__ == "__main__":
    asyncio.run(stress_test())
```

## 최적화 체크리스트

### 성능 목표
- [ ] 명령어 응답 시간 < 50ms
- [ ] AI 분석 시작 시간 < 100ms
- [ ] 메모리 사용량 < 200MB
- [ ] CPU 사용률 < 20% (유휴 시)

### 최적화 확인
- [ ] 캐싱이 정상 작동
- [ ] 메모리 누수 없음
- [ ] 스레드 풀 크기 적절
- [ ] 비동기 작업 병렬 처리

### 모니터링
- [ ] 성능 메트릭 수집
- [ ] 리소스 사용량 추적
- [ ] 병목 지점 식별
- [ ] 주기적 프로파일링

## 다음 단계

최적화가 완료되면 체크포인트 파일들을 작성하고 전체 시스템을 테스트합니다.