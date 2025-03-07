from typing import List, Any, Optional
import jinja2
from webcli2.core.ai import Task, AgenticMixin, Tool, Message, MessageRole, CompositeTask, cli_print, AIThinker, AIAgentInfo
from pydantic import BaseModel, Field, ConfigDict
from webcli2.core.ai.libs.oracle import OracleTools

class JQLQueryTool(Tool):
    class InputType(BaseModel):
        jql_query: str = Field(..., description="The JQL Query String") # Make the description easy to understand by LLM
        store_key: str = Field(..., description="The name after storte the result as")
        model_config = ConfigDict(extra='forbid')

    def __init__(self):
        super().__init__(name="run_jql_query", description="Execute JQL Query", input_type=self.InputType)

    def run(self, input:InputType):
        cli_print(f"JQLQueryTool: executing JQL, query: \"{input.jql_query}\"")
        oracle_tools = OracleTools()
        issues = oracle_tools.jira_execute_jql(input.jql_query)
        cli_print(f"JQLQueryTool: query done.")
        return issues, input.store_key

class JiraExpert(Task, AgenticMixin):
    description = """
JiraExpert
    For Jira related question, pelase ask me.
    For example, you can ask me: Can you query jira, return tickets for the proiject ABC, store the result as jira_issues.
"""
    def __init__(self, parent:Task):
        super().__init__(
            name="Jira Expert", 
            parent=parent
        )
        self.add_tool(JQLQueryTool())

    def run(self):
        cli_print(f"JiraExpert: run")
        if self.is_finished():
            return
        
        prompt = self.get_variable("prompt")
        actual_promot = f"""\
{prompt}
Instructions:
- To run JQL query, use tool `run_jql_query`.
- Use the provided tool to fetch data.
"""
        _, results = self.ask_llm([Message(role=MessageRole.USER, content=actual_promot)])
        result = results['run_jql_query']
        jira_issues = result[0]
        result_key = result[1]
        self.set_variable("result", jira_issues)
        self.parent.set_variable(result_key, jira_issues)
        self.set_finished()
