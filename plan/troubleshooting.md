# 문제 해결 가이드

## 일반적인 문제와 해결 방법

### 1. 설치 및 환경 설정

#### Python 버전 오류
**문제**: `Python 3.8 이상이 필요합니다` 오류
```bash
python --version
# Python 3.7.x
```

**해결**:
```bash
# macOS (Homebrew)
brew install python@3.11
python3.11 -m venv venv

# Linux
sudo apt update
sudo apt install python3.11 python3.11-venv

# 가상환경 재생성
python3.11 -m venv venv
source venv/bin/activate
```

#### 패키지 설치 실패
**문제**: `uv sync` 또는 의존성 설치 실패

**해결**:
```bash
# uv 업그레이드
uv self update

# 캐시 삭제 후 재설치
uv cache clean
uv sync --reinstall

# 특정 패키지 문제시
uv add textual==0.47.1 --force
```

### 2. Ollama 관련 문제

#### Ollama 서버 연결 실패
**문제**: `Connection refused` 또는 `Ollama 서버가 실행중이 아닙니다`

**해결**:
```bash
# Ollama 서버 시작
ollama serve

# 포트 확인
lsof -i :11434

# 다른 포트 사용
OLLAMA_HOST=http://localhost:8080 ollama serve

# .env 파일 수정
OLLAMA_HOST=http://localhost:8080
```

#### 모델 다운로드 실패
**문제**: `pull model: file does not exist`

**해결**:
```bash
# 사용 가능한 모델 확인
ollama list

# 모델 재다운로드
ollama rm codellama:7b
ollama pull codellama:7b

# 대체 모델 사용
ollama pull mistral:7b
```

#### 느린 AI 응답
**문제**: AI 응답이 5초 이상 걸림

**해결**:
```python
# config.py 수정
OLLAMA_CONFIG = {
    "model": "mistral:7b",  # 더 작은 모델
    "max_tokens": 200,      # 토큰 수 제한
    "temperature": 0.5,     # 낮은 temperature
    "num_ctx": 2048        # 컨텍스트 크기 축소
}
```

### 3. 터미널 에뮬레이션 문제

#### PTY 권한 오류
**문제**: `[Errno 13] Permission denied: '/dev/ptmx'`

**해결**:
```bash
# 권한 확인
ls -la /dev/ptmx

# macOS/Linux
sudo chmod 666 /dev/ptmx

# 또는 사용자 그룹 추가
sudo usermod -a -G tty $USER
# 로그아웃 후 재로그인
```

#### 한글 깨짐
**문제**: 한글 출력이 `???`로 표시

**해결**:
```bash
# 로케일 설정
export LANG=ko_KR.UTF-8
export LC_ALL=ko_KR.UTF-8

# .bashrc 또는 .zshrc에 추가
echo 'export LANG=ko_KR.UTF-8' >> ~/.bashrc
echo 'export LC_ALL=ko_KR.UTF-8' >> ~/.bashrc
```

#### 특수 키 작동 안함
**문제**: 화살표 키, 백스페이스 등이 이상하게 동작

**해결**:
```python
# terminal/emulator.py 수정
def handle_special_keys(self, key):
    key_map = {
        'KEY_UP': b'\x1b[A',
        'KEY_DOWN': b'\x1b[B',
        'KEY_RIGHT': b'\x1b[C',
        'KEY_LEFT': b'\x1b[D',
        'KEY_BACKSPACE': b'\x7f',
    }
    return key_map.get(key, key.encode())
```

### 4. UI/TUI 문제

#### Textual 렌더링 오류
**문제**: UI가 깨지거나 제대로 표시되지 않음

**해결**:
```bash
# 터미널 타입 확인
echo $TERM
# xterm-256color이어야 함

# 설정
export TERM=xterm-256color

# Windows Terminal 사용시
# 설정에서 "Use legacy console" 비활성화
```

#### 키보드 단축키 충돌
**문제**: Ctrl+C가 앱을 종료하지 않고 터미널로 전달됨

**해결**:
```python
# ui/app.py에서 우선순위 조정
BINDINGS = [
    Binding("ctrl+q", "quit", "Quit", priority=True),
    Binding("ctrl+c", "interrupt", "Interrupt"),
]
```

#### 레이아웃 비율 문제
**문제**: 터미널과 사이드바 비율이 이상함

**해결**:
```css
/* app.py의 CSS 수정 */
TerminalWidget {
    width: 2fr;  /* 비율 사용 */
}

AISidebar {
    width: 1fr;
    min-width: 30;  /* 최소 너비 */
}
```

### 5. 성능 문제

#### 높은 CPU 사용률
**문제**: 유휴 상태에서도 CPU 20% 이상 사용

**해결**:
```python
# 폴링 간격 조정
# terminal/emulator.py
async def read_output(self):
    while self.running:
        await asyncio.sleep(0.05)  # 0.01 -> 0.05
        # ...

# 불필요한 렌더링 방지
# ui/terminal_widget.py
def should_refresh(self):
    return self.has_new_content
```

#### 메모리 누수
**문제**: 장시간 사용 시 메모리 계속 증가

**해결**:
```python
# 주기적 정리 추가
# utils/memory_optimizer.py
async def periodic_cleanup(self):
    while True:
        await asyncio.sleep(300)  # 5분마다

        # 오래된 캐시 제거
        self.cleanup_old_cache()

        # 가비지 컬렉션
        gc.collect()

        # 히스토리 크기 제한
        if len(self.history) > 1000:
            self.history = self.history[-500:]
```

### 6. 실시간 기능 문제

#### AI 응답이 표시되지 않음
**문제**: 에러 발생해도 AI가 반응하지 않음

**해결**:
```python
# 트리거 확인
# ai/triggers.py
def debug_triggers(self, context):
    for trigger in self.triggers:
        matched = trigger.matches(context)
        print(f"{trigger.name}: {matched}")

# 이벤트 버스 확인
# utils/events.py
async def emit(self, event):
    logger.debug(f"Event emitted: {event.type}")
    await self.event_queue.put(event)
```

#### UI 업데이트 지연
**문제**: AI 응답이 늦게 표시됨

**해결**:
```python
# 즉시 업데이트
# ui/realtime_updates.py
def update_immediately(self, message):
    self.app.call_from_thread(
        self._update_ui_now,
        message
    )
```

### 7. 디버깅 방법

#### 로그 활성화
```bash
# 실행 시 디버그 모드
python main.py --debug

# 환경 변수로 설정
export LOG_LEVEL=DEBUG
python main.py
```

#### 로그 파일 위치
```bash
# 앱 로그
tail -f app.log

# Ollama 로그
tail -f ~/.ollama/logs/server.log

# 시스템 로그
journalctl -f -u ollama  # Linux
```

#### 프로파일링
```bash
# CPU 프로파일링
python -m cProfile -o profile.stats main.py

# 메모리 프로파일링
uv add --dev memory_profiler
uv run python -m memory_profiler main.py
```

### 8. 일반적인 에러 메시지

#### `ModuleNotFoundError: No module named 'terminal'`
```bash
# PYTHONPATH 설정
export PYTHONPATH="${PYTHONPATH}:$(pwd)"

# 또는 개발 모드 설치
uv pip install -e .
```

#### `asyncio.TimeoutError`
```python
# 타임아웃 늘리기
# ai/ollama_client.py
self.timeout = 60  # 30 -> 60초
```

#### `BrokenPipeError: [Errno 32] Broken pipe`
```python
# 파이프 에러 처리
try:
    os.write(self.master_fd, data)
except BrokenPipeError:
    self.restart_terminal()
```

### 9. 플랫폼별 문제

#### macOS
- **문제**: `illegal hardware instruction`
- **해결**: Rosetta 2 설치 또는 ARM64 네이티브 파이썬 사용

#### Windows (WSL2)
- **문제**: 터미널 색상 미지원
- **해결**: Windows Terminal 사용 권장

#### Linux
- **문제**: `GLIBC_2.XX not found`
- **해결**: 시스템 업데이트 또는 컨테이너 사용

### 10. 도움 받기

#### 로그 수집
```bash
# 진단 정보 수집 스크립트
./collect_diagnostics.sh

# 수동 수집
echo "=== System Info ===" > diagnostics.txt
uname -a >> diagnostics.txt
python --version >> diagnostics.txt
uv pip list >> diagnostics.txt
echo "=== Logs ===" >> diagnostics.txt
tail -n 100 app.log >> diagnostics.txt
```

#### 커뮤니티
- GitHub Issues: 버그 리포트 및 기능 요청
- Discord: 실시간 도움
- Stack Overflow: `terminal-ai-assistant` 태그

#### 추가 리소스
- [Textual 문서](https://textual.textualize.io/)
- [Ollama 문서](https://ollama.ai/docs)
- [Python asyncio 가이드](https://docs.python.org/3/library/asyncio.html)
