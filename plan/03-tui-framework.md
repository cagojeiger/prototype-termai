# 03. Textual TUI 프레임워크 구축

## 목표
Textual을 사용하여 터미널 패널과 AI 사이드바가 있는 TUI 인터페이스를 구축합니다.

## Textual 핵심 개념

### 1. App (애플리케이션)
- TUI 애플리케이션의 메인 컨테이너
- 이벤트 루프 관리
- 화면 렌더링 제어

### 2. Widget (위젯)
- UI의 기본 구성 요소
- 자체 렌더링과 이벤트 처리

### 3. Reactive (반응형 속성)
- 값이 변경되면 자동으로 UI 업데이트
- 상태 관리의 핵심

## Step 1: 기본 애플리케이션 구조

### ui/app.py
```python
from textual.app import App, ComposeResult
from textual.widgets import Header, Footer
from textual.containers import Horizontal, Vertical
from textual.binding import Binding
from textual.reactive import reactive

from .terminal_widget import TerminalWidget
from .ai_sidebar import AISidebar
from ..terminal.manager import TerminalManager
from ..ai.ollama_client import OllamaClient


class TerminalAIApp(App):
    """Terminal AI Assistant 메인 애플리케이션"""
    
    CSS = """
    Screen {
        layout: vertical;
    }
    
    #main-container {
        height: 100%;
        layout: horizontal;
    }
    
    TerminalWidget {
        width: 65%;
        border: solid $primary;
    }
    
    AISidebar {
        width: 35%;
        border: solid $secondary;
        margin-left: 1;
    }
    
    TerminalWidget:focus {
        border: solid $accent;
    }
    """
    
    BINDINGS = [
        Binding("ctrl+c", "quit", "Quit", priority=True),
        Binding("ctrl+l", "clear_terminal", "Clear Terminal"),
        Binding("ctrl+a", "toggle_ai", "Toggle AI"),
        Binding("f1", "help", "Help"),
        Binding("ctrl+s", "save_session", "Save Session"),
    ]
    
    # 반응형 속성
    ai_enabled = reactive(True)
    
    def __init__(self):
        super().__init__()
        self.terminal_manager = TerminalManager()
        self.ollama_client = OllamaClient()
        
    def compose(self) -> ComposeResult:
        """UI 구성"""
        yield Header()
        
        with Horizontal(id="main-container"):
            yield TerminalWidget(self.terminal_manager)
            yield AISidebar(self.ollama_client)
            
        yield Footer()
        
    def on_mount(self) -> None:
        """앱 마운트 시 호출"""
        # 터미널 시작
        self.terminal_manager.start()
        
        # 타이틀 설정
        self.title = "Terminal AI Assistant"
        self.sub_title = "AI-powered terminal experience"
        
        # 터미널 위젯에 포커스
        self.query_one(TerminalWidget).focus()
        
    def on_unmount(self) -> None:
        """앱 언마운트 시 호출"""
        self.terminal_manager.stop()
        
    def action_quit(self) -> None:
        """종료 액션"""
        self.exit()
        
    def action_clear_terminal(self) -> None:
        """터미널 클리어"""
        terminal = self.query_one(TerminalWidget)
        terminal.clear()
        
    def action_toggle_ai(self) -> None:
        """AI 토글"""
        self.ai_enabled = not self.ai_enabled
        sidebar = self.query_one(AISidebar)
        sidebar.set_enabled(self.ai_enabled)
        
    def action_help(self) -> None:
        """도움말 표시"""
        # TODO: 도움말 팝업 구현
        pass
        
    def action_save_session(self) -> None:
        """세션 저장"""
        # TODO: 세션 저장 구현
        pass
```

## Step 2: 터미널 위젯 구현

### ui/terminal_widget.py
```python
from textual.widget import Widget
from textual.reactive import reactive
from textual.geometry import Size
from textual.strip import Strip
from textual.message import Message
from textual import events
from rich.segment import Segment
from rich.style import Style
from typing import List
import asyncio

from ..terminal.manager import TerminalManager


class TerminalWidget(Widget):
    """터미널 디스플레이 위젯"""
    
    # 반응형 속성
    cursor_position = reactive((0, 0))
    scroll_offset = reactive(0)
    
    def __init__(self, terminal_manager: TerminalManager):
        super().__init__()
        self.terminal_manager = terminal_manager
        self.can_focus = True
        
        # 디스플레이 버퍼
        self.display_lines: List[str] = []
        
        # 출력 핸들러 설정
        self.terminal_manager.emulator.on_output = self._handle_output
        
        # 입력 버퍼
        self.input_buffer = ""
        
    def _handle_output(self, data: bytes):
        """터미널 출력 처리"""
        # UI 스레드에서 업데이트
        self.app.call_from_thread(self._update_display)
        
    def _update_display(self):
        """디스플레이 업데이트"""
        # 터미널 출력 가져오기
        self.display_lines = self.terminal_manager.get_output()
        
        # 자동 스크롤
        if self.scroll_offset == len(self.display_lines) - self.size.height:
            self.scroll_offset = max(0, len(self.display_lines) - self.size.height)
            
        self.refresh()
        
    def render_line(self, y: int) -> Strip:
        """라인 렌더링"""
        line_idx = y + self.scroll_offset
        
        if line_idx < len(self.display_lines):
            line = self.display_lines[line_idx]
            segments = self._parse_line(line)
            return Strip(segments)
        else:
            return Strip([])
            
    def _parse_line(self, line: str) -> List[Segment]:
        """ANSI 코드 파싱 및 세그먼트 생성"""
        # 간단한 구현 - 실제로는 더 복잡한 ANSI 파서 필요
        segments = []
        
        # 기본 스타일
        style = Style(color="white", bgcolor="black")
        
        # 텍스트를 세그먼트로 변환
        segments.append(Segment(line, style))
        
        return segments
        
    def on_key(self, event: events.Key) -> None:
        """키 입력 처리"""
        key = event.key
        
        if key == "enter":
            # 명령어 실행
            self.terminal_manager.execute(self.input_buffer)
            self.input_buffer = ""
            
        elif key == "backspace":
            if self.input_buffer:
                self.input_buffer = self.input_buffer[:-1]
                self.terminal_manager.emulator.write(b'\x08 \x08')  # 백스페이스
                
        elif key == "ctrl+c":
            # 인터럽트 시그널
            self.terminal_manager.emulator.write(b'\x03')
            
        elif key == "ctrl+d":
            # EOF
            self.terminal_manager.emulator.write(b'\x04')
            
        elif key == "up":
            # 히스토리 위로
            # TODO: 히스토리 네비게이션 구현
            pass
            
        elif key == "down":
            # 히스토리 아래로
            pass
            
        elif len(key) == 1:
            # 일반 문자 입력
            self.input_buffer += key
            self.terminal_manager.emulator.write(key.encode('utf-8'))
            
    def on_mouse_scroll_down(self, event: events.MouseScrollDown) -> None:
        """마우스 스크롤 다운"""
        max_scroll = max(0, len(self.display_lines) - self.size.height)
        self.scroll_offset = min(self.scroll_offset + 3, max_scroll)
        
    def on_mouse_scroll_up(self, event: events.MouseScrollUp) -> None:
        """마우스 스크롤 업"""
        self.scroll_offset = max(0, self.scroll_offset - 3)
        
    def clear(self):
        """터미널 클리어"""
        self.terminal_manager.clear_output()
        self.display_lines = []
        self.scroll_offset = 0
        self.refresh()
        
    def on_resize(self, event: events.Resize) -> None:
        """리사이즈 처리"""
        # 터미널 크기 업데이트
        self.terminal_manager.resize(event.size.width, event.size.height)
```

## Step 3: AI 사이드바 위젯

### ui/ai_sidebar.py
```python
from textual.widget import Widget
from textual.widgets import Static, Label, ScrollView, Button
from textual.containers import Vertical, Horizontal
from textual.reactive import reactive
from textual.message import Message
from datetime import datetime
from typing import List, Optional
from rich.text import Text
from rich.panel import Panel

from ..ai.ollama_client import OllamaClient


class AIMessage(Static):
    """AI 메시지 디스플레이"""
    
    def __init__(self, content: str, msg_type: str = "info"):
        super().__init__()
        self.content = content
        self.msg_type = msg_type
        self.timestamp = datetime.now()
        
    def render(self):
        """메시지 렌더링"""
        # 메시지 타입별 스타일
        styles = {
            "info": "cyan",
            "warning": "yellow", 
            "error": "red",
            "success": "green",
            "suggestion": "blue"
        }
        
        style = styles.get(self.msg_type, "white")
        time_str = self.timestamp.strftime("%H:%M:%S")
        
        # 패널로 메시지 표시
        text = Text(self.content, style=style)
        return Panel(
            text,
            title=f"[{self.msg_type.upper()}] {time_str}",
            title_align="left",
            border_style=style
        )


class AISidebar(Widget):
    """AI 어시스턴트 사이드바"""
    
    # 반응형 속성
    is_enabled = reactive(True)
    is_processing = reactive(False)
    
    def __init__(self, ollama_client: OllamaClient):
        super().__init__()
        self.ollama_client = ollama_client
        self.messages: List[AIMessage] = []
        
    def compose(self):
        """UI 구성"""
        with Vertical():
            # 헤더
            yield Label("🤖 AI Assistant", id="ai-header")
            
            # 상태 표시
            yield Static("", id="ai-status")
            
            # 메시지 스크롤 영역
            with ScrollView(id="ai-messages"):
                yield Vertical(id="message-container")
                
            # 컨트롤 버튼
            with Horizontal(id="ai-controls"):
                yield Button("Clear", id="clear-btn", variant="warning")
                yield Button("Analyze", id="analyze-btn", variant="primary")
                
    def on_mount(self):
        """마운트 시 초기화"""
        self._update_status()
        
    def set_enabled(self, enabled: bool):
        """AI 활성화/비활성화"""
        self.is_enabled = enabled
        self._update_status()
        
    def _update_status(self):
        """상태 업데이트"""
        status = self.query_one("#ai-status", Static)
        
        if not self.is_enabled:
            status.update("🔴 AI Disabled")
        elif self.is_processing:
            status.update("🟡 Processing...")
        else:
            status.update("🟢 AI Active")
            
    def add_message(self, content: str, msg_type: str = "info"):
        """새 메시지 추가"""
        message = AIMessage(content, msg_type)
        self.messages.append(message)
        
        # 메시지 컨테이너에 추가
        container = self.query_one("#message-container", Vertical)
        container.mount(message)
        
        # 스크롤 다운
        scroll_view = self.query_one("#ai-messages", ScrollView)
        scroll_view.scroll_end()
        
    async def analyze_context(self, context: dict):
        """컨텍스트 분석"""
        if not self.is_enabled or self.is_processing:
            return
            
        self.is_processing = True
        self._update_status()
        
        try:
            # AI 분석 요청
            response = await self.ollama_client.analyze(context)
            
            # 응답 처리
            if response.get("error"):
                self.add_message(f"Error: {response['error']}", "error")
            else:
                # 제안사항
                if response.get("suggestions"):
                    for suggestion in response["suggestions"]:
                        self.add_message(suggestion, "suggestion")
                        
                # 경고
                if response.get("warnings"):
                    for warning in response["warnings"]:
                        self.add_message(warning, "warning")
                        
        except Exception as e:
            self.add_message(f"AI Error: {str(e)}", "error")
            
        finally:
            self.is_processing = False
            self._update_status()
            
    def on_button_pressed(self, event: Button.Pressed):
        """버튼 클릭 처리"""
        if event.button.id == "clear-btn":
            self.clear_messages()
        elif event.button.id == "analyze-btn":
            # 수동 분석 트리거
            self.app.call_later(self._trigger_analysis)
            
    def clear_messages(self):
        """메시지 클리어"""
        self.messages.clear()
        container = self.query_one("#message-container", Vertical)
        container.remove_children()
        
    async def _trigger_analysis(self):
        """수동 분석 트리거"""
        # TODO: 현재 컨텍스트 수집 및 분석
        context = {
            "command": "test",
            "output": "test output"
        }
        await self.analyze_context(context)
```

## Step 4: 메인 애플리케이션 실행

### main.py
```python
#!/usr/bin/env python3
import asyncio
import sys
from pathlib import Path

# 프로젝트 루트를 Python 경로에 추가
sys.path.insert(0, str(Path(__file__).parent))

from ui.app import TerminalAIApp
from utils.config import load_config


async def main():
    """메인 실행 함수"""
    # 설정 로드
    config = load_config()
    
    # 애플리케이션 생성 및 실행
    app = TerminalAIApp()
    await app.run_async()


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\nApplication terminated by user")
        sys.exit(0)
```

## Step 5: 테스트 및 스타일링

### test_ui.py
```python
#!/usr/bin/env python3
from textual.app import App, ComposeResult
from textual.widgets import Header, Footer, Label, Button, Static
from textual.containers import Horizontal, Vertical, ScrollableContainer
from textual.reactive import reactive
from rich.panel import Panel
from rich.text import Text


class UITestApp(App):
    """UI 컴포넌트 테스트 앱"""
    
    CSS = """
    Screen {
        background: $surface;
    }
    
    #left-panel {
        width: 65%;
        height: 100%;
        border: solid $primary;
        padding: 1;
    }
    
    #right-panel {
        width: 35%;
        height: 100%;
        border: solid $secondary;
        padding: 1;
        margin-left: 1;
    }
    
    .test-button {
        margin: 1;
        width: 100%;
    }
    """
    
    counter = reactive(0)
    
    def compose(self) -> ComposeResult:
        yield Header()
        
        with Horizontal():
            # 왼쪽 패널 (터미널 시뮬레이션)
            with Vertical(id="left-panel"):
                yield Label("Terminal Area", id="terminal-label")
                with ScrollableContainer():
                    yield Static(self.get_sample_terminal_output())
                    
            # 오른쪽 패널 (AI 사이드바)
            with Vertical(id="right-panel"):
                yield Label("AI Assistant", id="ai-label")
                yield Static(f"Counter: {self.counter}")
                yield Button("Increment", id="inc-btn", classes="test-button")
                yield Button("Add Message", id="msg-btn", classes="test-button")
                
                with ScrollableContainer(id="messages"):
                    yield Static("AI messages will appear here...")
                    
        yield Footer()
        
    def get_sample_terminal_output(self) -> Panel:
        """샘플 터미널 출력"""
        text = Text()
        text.append("$ ", style="bold green")
        text.append("ls -la\n")
        text.append("total 24\n", style="dim")
        text.append("drwxr-xr-x  5 user  staff   160 Jan  1 12:00 .\n")
        text.append("drwxr-xr-x 20 user  staff   640 Jan  1 11:00 ..\n")
        text.append("-rw-r--r--  1 user  staff  1234 Jan  1 12:00 app.py\n")
        text.append("\n$ ", style="bold green")
        text.append("python app.py", style="yellow")
        
        return Panel(text, title="Terminal Output", border_style="green")
        
    def on_button_pressed(self, event: Button.Pressed):
        """버튼 이벤트 처리"""
        if event.button.id == "inc-btn":
            self.counter += 1
            self.query_one("#right-panel Static").update(f"Counter: {self.counter}")
            
        elif event.button.id == "msg-btn":
            messages = self.query_one("#messages")
            new_msg = Static(f"AI Message #{self.counter}", classes="ai-message")
            messages.mount(new_msg)
            messages.scroll_end()


if __name__ == "__main__":
    app = UITestApp()
    app.run()
```

## Checkpoint 2: TUI 기본 동작 확인

### 실행 방법
```bash
# UI 테스트
python test_ui.py

# 메인 애플리케이션 (터미널 통합 필요)
python main.py
```

### 체크리스트
- [ ] Textual 앱이 정상적으로 실행됨
- [ ] 레이아웃이 올바르게 분할됨 (65% / 35%)
- [ ] 키보드 단축키가 작동함 (Ctrl+C, Ctrl+L 등)
- [ ] 스크롤이 정상 작동함
- [ ] 버튼 클릭 이벤트가 처리됨
- [ ] 반응형 속성이 UI를 업데이트함
- [ ] 리사이즈 시 레이아웃이 유지됨

### 예상 화면
```
┌─ Terminal AI Assistant ─────────────────────────────┐
│ ┌─────────────────────┬──────────────────┐         │
│ │                     │ 🤖 AI Assistant  │         │
│ │  Terminal Area      │ 🟢 AI Active     │         │
│ │                     │                  │         │
│ │  $ ls -la          │ [Clear] [Analyze]│         │
│ │  total 24          │                  │         │
│ │  drwxr-xr-x ...    │ AI messages will │         │
│ │                     │ appear here...   │         │
│ │  $ _               │                  │         │
│ │                     │                  │         │
│ └─────────────────────┴──────────────────┘         │
│ Ctrl+C Quit  Ctrl+L Clear  Ctrl+A Toggle AI  F1    │
└─────────────────────────────────────────────────────┘
```

## 문제 해결

### 1. Import 오류
```python
# PYTHONPATH 설정
export PYTHONPATH=/path/to/project:$PYTHONPATH
```

### 2. 렌더링 문제
```python
# 터미널 타입 확인
echo $TERM
# xterm-256color 권장

# 강제 설정
export TERM=xterm-256color
```

### 3. 한글 깨짐
```python
# 로케일 설정
export LANG=ko_KR.UTF-8
export LC_ALL=ko_KR.UTF-8
```

## 다음 단계

TUI 프레임워크가 구축되면 [04-ollama-integration.md](04-ollama-integration.md)로 진행하여 AI 기능을 통합합니다.