"""
AI Sidebar - AI Assistant Panel Component

This module contains the AI sidebar widget that displays AI responses,
status, and controls in the 35% right panel of the application.
"""

from datetime import datetime
from typing import List, Tuple

from textual.containers import Horizontal, ScrollableContainer, Vertical
from textual.message import Message
from textual.reactive import reactive
from textual.widgets import Button, Static


class AISidebar(Static):
    """AI Assistant panel (35% width)."""

    ai_status = reactive(True)
    message_count = reactive(0)

    class AIMessage(Message):
        """Message sent when AI produces a response."""

        def __init__(self, title: str, content: str) -> None:
            self.title = title
            self.content = content
            super().__init__()

    def __init__(self, ai_analyzer=None, **kwargs):
        """Initialize the AI sidebar.

        Args:
            ai_analyzer: Optional RealtimeAnalyzer instance for AI features
            **kwargs: Additional keyword arguments passed to Static
        """
        super().__init__(**kwargs)
        self.ai_analyzer = ai_analyzer
        self.messages: List[Tuple[str, str, str]] = []  # (timestamp, title, content)
        self.is_analyzing = False

        if self.ai_analyzer:
            self._register_ai_callbacks()

    def compose(self):
        """Compose the AI sidebar layout."""
        with Vertical():
            yield Static("🤖 AI Assistant", id="ai-title", classes="title")
            yield Static("🟢 AI Active", id="ai-status", classes="status")

            with ScrollableContainer(id="ai-messages"):
                yield Static(
                    "AI 어시스턴트가 준비되었습니다.\n\n명령어를 실행하면 실시간으로 분석하고 도움을 제공합니다.",
                    id="welcome-message",
                    classes="message",
                )

            with Horizontal(id="ai-controls"):
                yield Button("Clear", id="clear-btn", variant="primary")
                yield Button("Analyze", id="analyze-btn", variant="success")

    def on_mount(self) -> None:
        """Called when the widget is mounted."""
        self.can_focus = True
        self._update_status_display()

    def watch_ai_status(self, ai_status: bool) -> None:
        """React to AI status changes."""
        self._update_status_display()

    def _update_status_display(self) -> None:
        """Update the AI status display."""
        try:
            status_widget = self.query_one("#ai-status", Static)

            if self.ai_status:
                status_widget.update("🟢 AI Active")
                status_widget.remove_class("disabled")
                status_widget.add_class("active")
            else:
                status_widget.update("🔴 AI Disabled")
                status_widget.remove_class("active")
                status_widget.add_class("disabled")
        except Exception:
            pass

    def set_ai_status(self, enabled: bool) -> None:
        """Set the AI status."""
        self.ai_status = enabled

        if enabled:
            self.add_message("시스템", "AI 어시스턴트가 활성화되었습니다.")
        else:
            self.add_message("시스템", "AI 어시스턴트가 비활성화되었습니다.")

    def add_message(self, title: str, content: str) -> None:
        """Add a new message to the AI sidebar."""
        timestamp = datetime.now().strftime("%H:%M:%S")
        self.messages.append((timestamp, title, content))
        self.message_count += 1

        self._update_messages_display()

    def _update_messages_display(self) -> None:
        """Update the messages display."""
        messages_container = self.query_one("#ai-messages", ScrollableContainer)

        messages_container.remove_children()

        for timestamp, title, content in self.messages:
            message_widget = Static(
                f"[{timestamp}] {title}\n{content}\n", classes="message"
            )
            messages_container.mount(message_widget)

        messages_container.scroll_end()

    def clear_messages(self) -> None:
        """Clear all messages."""
        self.messages.clear()
        self.message_count = 0

        messages_container = self.query_one("#ai-messages", ScrollableContainer)
        messages_container.remove_children()

        welcome_widget = Static(
            "메시지가 지워졌습니다.\n\n새로운 명령어를 실행하면 AI 분석이 시작됩니다.", classes="message"
        )
        messages_container.mount(welcome_widget)

    def on_button_pressed(self, event: Button.Pressed) -> None:
        """Handle button press events."""
        if event.button.id == "clear-btn":
            self._handle_clear_button()
        elif event.button.id == "analyze-btn":
            self._handle_analyze_button()

    def _handle_clear_button(self) -> None:
        """Handle Clear button press."""
        self.clear_messages()
        self.add_message("시스템", "메시지 기록이 지워졌습니다.")

    def _handle_analyze_button(self) -> None:
        """Handle Analyze button press."""
        if not self.ai_status:
            self.add_message("오류", "AI가 비활성화되어 있습니다. Ctrl+A로 활성화하세요.")
            return

        if self.is_analyzing:
            self.add_message("알림", "이미 분석이 진행 중입니다. 잠시 기다려주세요.")
            return

        self.is_analyzing = True
        self.add_message("분석", "🔄 현재 터미널 컨텍스트를 분석 중입니다...")

        if self.ai_analyzer:
            self._request_ai_analysis()
        else:
            self._show_placeholder_analysis()

    def _request_ai_analysis(self) -> None:
        """Request AI analysis from the analyzer."""
        if self.ai_analyzer:
            import asyncio

            try:
                loop = asyncio.get_event_loop()
                loop.create_task(self._perform_ai_analysis())
            except RuntimeError:
                asyncio.run(self._perform_ai_analysis())
        else:
            self._show_placeholder_analysis()

    async def _perform_ai_analysis(self) -> None:
        """Perform actual AI analysis using the analyzer."""
        if not self.ai_analyzer:
            self._show_placeholder_analysis()
            return

        try:
            context_summary = self.ai_analyzer.context_manager.get_context_summary()
            response = await self.ai_analyzer.suggest_commands(
                intent="분석 현재 터미널 상태와 제안사항 제공", context=context_summary
            )

            if response and response.content:
                self.add_message("AI 분석", response.content)
            else:
                self.add_message(
                    "AI 분석", "✅ AI 시스템이 연결되어 있습니다.\n현재 컨텍스트에서 특별한 제안사항이 없습니다."
                )

        except Exception as e:
            self.add_message("AI 오류", f"AI 분석 중 오류가 발생했습니다: {str(e)}")
            self.is_analyzing = False
            self._show_placeholder_analysis()

    def _show_placeholder_analysis(self) -> None:
        """Show placeholder AI analysis (for testing)."""
        analysis_result = """
📊 터미널 분석 결과:

✅ 현재 상태: 정상
📁 작업 디렉토리: /home/ubuntu/repos/prototype-termai
🔧 최근 명령어: 없음

💡 제안사항:
• 프로젝트 구조를 확인하려면 'ls -la' 실행
• Git 상태를 확인하려면 'git status' 실행
• 테스트를 실행하려면 'uv run python test_terminal.py' 실행

⚠️ 주의사항:
• 현재 테스트 모드에서 실행 중입니다
• 실제 터미널 통합은 다음 단계에서 구현됩니다
        """

        self.add_message("AI 분석", analysis_result)

    def on_ai_response(self, response) -> None:
        """Handle AI response from the analyzer."""
        if hasattr(response, "content") and response.content:
            self.add_message("AI 응답", response.content)

        if hasattr(response, "suggestions") and response.suggestions:
            suggestions_text = "\n".join(
                [f"• {suggestion}" for suggestion in response.suggestions]
            )
            self.add_message("제안사항", suggestions_text)

    def on_focus(self) -> None:
        """Called when the widget gains focus."""
        self.add_class("focused")

    def on_blur(self) -> None:
        """Called when the widget loses focus."""
        self.remove_class("focused")

    def _register_ai_callbacks(self) -> None:
        """Register callbacks for AI analysis events."""
        if not self.ai_analyzer:
            return

        self.ai_analyzer.register_callback(
            "analysis_completed", self._on_analysis_completed
        )
        self.ai_analyzer.register_callback("error_analyzed", self._on_error_analyzed)
        self.ai_analyzer.register_callback(
            "commands_suggested", self._on_commands_suggested
        )
        self.ai_analyzer.register_callback("analysis_failed", self._on_analysis_failed)

    def _on_analysis_completed(self, data: dict) -> None:
        """Handle completed AI analysis."""
        response = data.get("response")
        if response and hasattr(response, "content"):
            self._display_ai_response("분석 완료", response.content)

    def _on_error_analyzed(self, data: dict) -> None:
        """Handle error analysis completion."""
        response = data.get("response")
        command = data.get("command", "")
        if response and hasattr(response, "content"):
            title = f"오류 분석: {command[:30]}..."
            self._display_ai_response(title, response.content)

    def _on_commands_suggested(self, data: dict) -> None:
        """Handle command suggestions."""
        response = data.get("response")
        intent = data.get("intent", "")
        if response and hasattr(response, "content"):
            title = f"명령어 제안: {intent[:20]}..."
            self._display_ai_response(title, response.content)

    def _on_analysis_failed(self, data: dict) -> None:
        """Handle failed AI analysis."""
        error = data.get("error", "알 수 없는 오류")
        self.add_message("AI 오류", f"분석 실패: {error}")
        self.is_analyzing = False

    def _display_ai_response(self, title: str, content: str) -> None:
        """Display AI response with improved formatting."""
        formatted_content = self._format_ai_content(content)
        self.add_message(title, formatted_content)
        self.is_analyzing = False

    def _format_ai_content(self, content: str) -> str:
        """Format AI response content for better display."""
        if not content:
            return "응답 내용이 없습니다."

        formatted = content.strip()

        formatted = formatted.replace("•", "\n• ")
        formatted = formatted.replace("- ", "\n• ")

        formatted = formatted.replace("제안사항:", "\n💡 제안사항:")
        formatted = formatted.replace("해결방법:", "\n🔧 해결방법:")
        formatted = formatted.replace("주의사항:", "\n⚠️ 주의사항:")
        formatted = formatted.replace("설명:", "\n📝 설명:")

        while "\n\n\n" in formatted:
            formatted = formatted.replace("\n\n\n", "\n\n")

        return formatted.strip()
