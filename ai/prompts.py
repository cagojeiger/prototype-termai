"""
Prompt Templates for Terminal AI Assistant

This module provides static methods for generating context-specific
prompts for the LLM based on different terminal scenarios.
"""

from typing import List, Optional
from .context import CommandContext, SessionContext


class PromptTemplate:
    """Static methods for generating context-specific prompts for LLM."""
    
    @staticmethod
    def error_analysis_prompt(
        command: str,
        error_output: str,
        context: Optional[str] = None,
        recent_commands: Optional[List[CommandContext]] = None
    ) -> str:
        """Generate prompt for analyzing command execution errors."""
        
        prompt = f"""You are an expert terminal AI assistant. A user executed a command that failed with an error.

COMMAND: {command}
ERROR OUTPUT:
{error_output}
"""
        
        if context:
            prompt += f"\nCONTEXT:\n{context}\n"
        
        if recent_commands:
            prompt += "\nRECENT COMMAND HISTORY:\n"
            for cmd in recent_commands[-3:]:  # Last 3 commands
                status = "✓" if cmd.exit_code == 0 else "✗"
                prompt += f"{status} {cmd.command}\n"
        
        prompt += """
Please provide a helpful analysis with:

1. **Root Cause**: What exactly went wrong and why?

2. **Solutions**: Specific commands or steps to fix this issue
   - Format each solution as: SUGGESTION: [specific command or action]
   - Prioritize the most likely solutions first

3. **Prevention**: How to avoid this error in the future
   - Format as: WARNING: [preventive advice]

4. **Context**: Any additional information that might be relevant

Keep your response concise, practical, and focused on actionable solutions. Use clear, simple language.
"""
        
        return prompt
    
    @staticmethod
    def command_suggestion_prompt(
        intent: str,
        session_context: SessionContext,
        recent_commands: Optional[List[CommandContext]] = None
    ) -> str:
        """Generate prompt for suggesting commands based on user intent."""
        
        prompt = f"""You are an expert terminal AI assistant. A user wants to accomplish something in their terminal.

USER INTENT: {intent}

CURRENT CONTEXT:
- Directory: {session_context.current_directory}
- Shell: {session_context.shell_type}
"""
        
        if session_context.git_status:
            git = session_context.git_status
            prompt += f"- Git: {git['branch']} branch ({'clean' if not git['has_changes'] else 'has changes'})\n"
        
        if recent_commands:
            prompt += "\nRECENT COMMANDS:\n"
            for cmd in recent_commands[-5:]:
                status = "✓" if cmd.exit_code == 0 else "✗"
                prompt += f"{status} {cmd.command}\n"
        
        prompt += """
Please suggest appropriate terminal commands to accomplish this goal:

1. **Primary Solutions**: Most direct ways to achieve the intent
   - Format as: SUGGESTION: [command] - [brief explanation]

2. **Alternative Approaches**: Other ways to accomplish the same goal
   - Format as: SUGGESTION: [command] - [brief explanation]

3. **Prerequisites**: Any setup or dependencies needed
   - Format as: WARNING: [requirement or consideration]

4. **Safety Notes**: Important warnings or considerations
   - Format as: WARNING: [safety advice]

Focus on commonly-used, safe commands. Provide specific examples rather than generic advice.
"""
        
        return prompt
    
    @staticmethod
    def output_analysis_prompt(
        command: str,
        output: str,
        session_context: SessionContext
    ) -> str:
        """Generate prompt for analyzing successful command output."""
        
        prompt = f"""You are an expert terminal AI assistant. A user executed a command successfully and you should provide insights about the results.

COMMAND: {command}
OUTPUT:
{output}

CONTEXT:
- Directory: {session_context.current_directory}
- Shell: {session_context.shell_type}
"""
        
        if session_context.git_status:
            git = session_context.git_status
            prompt += f"- Git: {git['branch']} branch\n"
        
        prompt += """
Please provide helpful insights about this command and its output:

1. **Summary**: Brief explanation of what the command accomplished

2. **Key Insights**: Important information from the output
   - Highlight any notable results, patterns, or findings

3. **Next Steps**: Useful follow-up commands or actions
   - Format as: SUGGESTION: [command] - [why it's useful]

4. **Observations**: Any potential issues or things to note
   - Format as: WARNING: [observation or concern]

Keep your response concise and focus on actionable insights. Don't repeat obvious information.
"""
        
        return prompt
    
    @staticmethod
    def dangerous_command_warning_prompt(
        command: str,
        session_context: SessionContext
    ) -> str:
        """Generate prompt for warning about potentially dangerous commands."""
        
        prompt = f"""You are a terminal safety AI assistant. A user is about to execute a potentially dangerous command.

DANGEROUS COMMAND: {command}

CONTEXT:
- Directory: {session_context.current_directory}
- Shell: {session_context.shell_type}
"""
        
        prompt += """
Please provide a safety analysis:

1. **Risk Assessment**: What could go wrong with this command?
   - Format as: WARNING: [specific risk]

2. **Impact**: What would happen if something goes wrong?
   - Be specific about potential consequences

3. **Safer Alternatives**: Less risky ways to accomplish the same goal
   - Format as: SUGGESTION: [safer command] - [explanation]

4. **Safety Measures**: If the user must run this command, how to do it safely
   - Format as: SUGGESTION: [safety precaution]

Be clear and direct about the risks, but also provide constructive alternatives.
"""
        
        return prompt
    
    @staticmethod
    def general_help_prompt(
        query: str,
        session_context: SessionContext,
        recent_commands: Optional[List[CommandContext]] = None
    ) -> str:
        """Generate prompt for general terminal help and questions."""
        
        prompt = f"""You are a helpful terminal AI assistant. A user has a question or needs help.

USER QUERY: {query}

CONTEXT:
- Directory: {session_context.current_directory}
- Shell: {session_context.shell_type}
"""
        
        if session_context.git_status:
            git = session_context.git_status
            prompt += f"- Git: {git['branch']} branch\n"
        
        if recent_commands:
            prompt += "\nRECENT ACTIVITY:\n"
            for cmd in recent_commands[-3:]:
                status = "✓" if cmd.exit_code == 0 else "✗"
                prompt += f"{status} {cmd.command}\n"
        
        prompt += """
Please provide helpful assistance:

1. **Direct Answer**: Address the user's question clearly

2. **Practical Examples**: Show specific commands or examples when relevant
   - Format as: SUGGESTION: [command] - [explanation]

3. **Additional Tips**: Related advice or best practices
   - Format as: SUGGESTION: [tip or command]

4. **Cautions**: Any warnings or things to be careful about
   - Format as: WARNING: [caution]

Be conversational, helpful, and practical. Focus on what the user can actually do.
"""
        
        return prompt
    
    @staticmethod
    def context_summary_prompt(
        session_context: SessionContext,
        recent_commands: List[CommandContext],
        error_commands: List[CommandContext]
    ) -> str:
        """Generate prompt for summarizing current terminal session context."""
        
        prompt = f"""You are a terminal AI assistant. Please provide a brief summary of the current terminal session.

CURRENT STATE:
- Directory: {session_context.current_directory}
- Shell: {session_context.shell_type}
"""
        
        if session_context.git_status:
            git = session_context.git_status
            prompt += f"- Git: {git['branch']} branch ({'clean' if not git['has_changes'] else 'modified'})\n"
        
        if recent_commands:
            prompt += "\nRECENT COMMANDS:\n"
            for cmd in recent_commands[-5:]:
                status = "✓" if cmd.exit_code == 0 else "✗"
                prompt += f"{status} {cmd.command}\n"
        
        if error_commands:
            prompt += "\nRECENT ERRORS:\n"
            for cmd in error_commands[:3]:
                prompt += f"✗ {cmd.command} (exit {cmd.exit_code})\n"
        
        prompt += """
Please provide:

1. **Session Summary**: What has the user been working on?

2. **Current Status**: What's the current state of their work?

3. **Potential Issues**: Any problems or concerns to address
   - Format as: WARNING: [issue or concern]

4. **Suggested Actions**: What might be useful to do next
   - Format as: SUGGESTION: [action or command]

Keep it concise and focus on the most relevant information.
"""
        
        return prompt
    
    @staticmethod
    def format_system_prompt() -> str:
        """Get the base system prompt for all interactions."""
        
        return """You are a helpful terminal AI assistant. Your role is to:

- Analyze terminal commands and their output
- Provide practical solutions to problems
- Suggest useful commands and workflows  
- Warn about potential risks or issues
- Help users learn and improve their terminal skills

Guidelines:
- Be concise and actionable
- Use specific commands and examples
- Format suggestions as "SUGGESTION: [command/action] - [explanation]"
- Format warnings as "WARNING: [concern or caution]"
- Focus on commonly-used, safe approaches
- Explain technical concepts in simple terms
- Prioritize user safety and data protection

Always aim to be helpful, accurate, and educational."""


def create_error_prompt(command: str, error: str, context: Optional[str] = None) -> str:
    """Quick helper to create error analysis prompt."""
    return PromptTemplate.error_analysis_prompt(command, error, context)


def create_help_prompt(query: str, context: SessionContext) -> str:
    """Quick helper to create general help prompt."""
    return PromptTemplate.general_help_prompt(query, context)


def create_suggestion_prompt(intent: str, context: SessionContext) -> str:
    """Quick helper to create command suggestion prompt."""
    return PromptTemplate.command_suggestion_prompt(intent, context)
