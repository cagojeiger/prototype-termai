"""
Terminal AI Assistant - Main TUI Application

This module contains the main Textual application class that orchestrates
the terminal and AI sidebar components in a split-panel interface.
"""

from textual.app import App, ComposeResult
from textual.containers import Horizontal
from textual.widgets import Header, Footer, Static
from .terminal_widget import TerminalWidget
from .ai_sidebar import AISidebar


class TerminalAIApp(App):
    """Main Terminal AI Assistant TUI Application."""
    
    TITLE = "Terminal AI Assistant"
    
    CSS = """
    .terminal-area {
        width: 65%;
        border: solid $primary;
        margin: 1;
        padding: 1;
    }
    
    .ai-sidebar {
        width: 35%;
        border: solid $secondary;
        margin: 1;
        padding: 1;
    }
    
    Header {
        dock: top;
        height: 3;
    }
    
    Footer {
        dock: bottom;
        height: 1;
    }
    """
    
    BINDINGS = [
        ("ctrl+c", "quit", "Quit"),
        ("ctrl+l", "clear_terminal", "Clear"),
        ("ctrl+a", "toggle_ai", "Toggle AI"),
        ("f1", "help", "Help"),
        ("tab", "focus_next", "Next Focus"),
    ]
    
    def compose(self) -> ComposeResult:
        """Compose the application layout."""
        yield Header()
        
        with Horizontal(id="main-container"):
            yield TerminalWidget(test_mode=True, classes="terminal-area")
            yield AISidebar(classes="ai-sidebar")
            
        yield Footer()
    
    def action_quit(self) -> None:
        """Quit the application."""
        self.exit()
    
    def action_clear_terminal(self) -> None:
        """Clear the terminal display."""
        try:
            terminal_widget = self.query_one(TerminalWidget)
            terminal_widget.clear()
        except Exception as e:
            self.log(f"Error clearing terminal: {e}")
    
    def action_toggle_ai(self) -> None:
        """Toggle AI assistance on/off."""
        try:
            ai_sidebar = self.query_one(AISidebar)
            ai_sidebar.set_ai_status(not ai_sidebar.ai_status)
        except Exception as e:
            self.log(f"Error toggling AI: {e}")
    
    def action_help(self) -> None:
        """Show help information."""
        try:
            ai_sidebar = self.query_one(AISidebar)
            help_message = """
🔧 Terminal AI Assistant - 도움말

⌨️ 키보드 단축키:
• Ctrl+C: 애플리케이션 종료
• Ctrl+L: 터미널 화면 지우기
• Ctrl+A: AI 어시스턴트 토글 (활성화/비활성화)
• F1: 이 도움말 표시
• Tab: 위젯 간 포커스 이동

🖥️ 터미널 영역 (왼쪽 65%):
• 터미널 명령어 입력 및 출력 표시
• 실시간 명령어 실행 결과 확인

🤖 AI 사이드바 (오른쪽 35%):
• AI 어시스턴트 상태 표시
• 실시간 분석 결과 및 제안사항
• Clear: 메시지 기록 지우기
• Analyze: 현재 컨텍스트 분석

💡 사용 팁:
• 터미널에서 명령어를 실행하면 AI가 자동으로 분석합니다
• 오류가 발생하면 AI가 해결 방법을 제안합니다
• Ctrl+A로 AI를 끄고 켤 수 있습니다
            """
            ai_sidebar.add_message("도움말", help_message.strip())
        except Exception as e:
            self.log(f"Error showing help: {e}")
    
    def action_focus_next(self) -> None:
        """Move focus to the next widget."""
        self.screen.focus_next()
