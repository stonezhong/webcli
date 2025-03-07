from typing import List, Any, Optional
import jinja2
from webcli2.core.ai import Task, AgenticMixin, Tool, Message, MessageRole, CompositeTask, cli_print, AIThinker, AIAgentInfo
from pydantic import BaseModel, Field, ConfigDict
from webcli2.core.ai.libs.oracle import OracleTools

class ConfluencePageUpdateTool(Tool):
    class InputType(BaseModel):
        html_content_key: str = Field(..., description="The name after pick the html content from stored value")
        model_config = ConfigDict(extra='forbid')
    
    def __init__(self):
        super().__init__(name="update_my_confluence_page", description="Update My Confluence Page", input_type=self.InputType)
    
    def run(self, input:InputType):
        return input

class ConfluenceExpert(Task, AgenticMixin):
    description = """
ConfluenceExpert
    For confluence related question, please ask me.
    For example, you can ask me: update my confluence page, pick the html content from stored value xyz.
"""    
    def __init__(self, parent:Task):
        super().__init__(
            name="Confluence Expert", 
            parent=parent
        )
        self.add_tool(ConfluencePageUpdateTool())

    def run(self):
        cli_print(f"ConfluenceExpert: run")
        if self.is_finished():
            return

        if not self.has_variable("html_content_key"):
            prompt = self.get_variable("prompt")
            actual_promot = f"""\
{prompt}
Instructions:
- To create my confluence page, use tool `update_my_confluence_page`.
- Use the provided tool to fetch data.
"""
            _, results = self.ask_llm([Message(role=MessageRole.USER, content=actual_promot)])
            result = results['update_my_confluence_page']
            self.set_variable("html_content_key", result.html_content_key)

        html_content_key = self.get_variable("html_content_key")
        if not self.parent.has_variable(html_content_key):
            return

        html_content = self.parent.get_variable(html_content_key)
        oracle_tools = OracleTools()
        oracle_tools.update_confluence_page("13970976799", title="AI Test Page", content=html_content)
        self.set_finished()
        cli_print(f"ConfluencePageUpdateTool: page updated!")
