import logging
logger = logging.getLogger(__name__)

from typing import Any, Dict, TypeVar, Generic, Type, Callable
from pydantic import BaseModel
import json
from openai import OpenAI

from webcli2.core.data import User

T = TypeVar('T', bound=BaseModel)

class ToolInfo(Generic[T]):
    input_type: Type[T]
    name: str
    description:str
    tool: Callable[[T], None]

    def __init__(self, *, input_type: Type[T], name:str, description:str, tool: Callable[[T], None]):
        self.input_type = input_type
        self.name = name
        self.description = description
        self.tool = tool


class AIAgent:
    tool_info_dict: Dict[str, ToolInfo]
    user: User
    openai_handler:Any

    def aitool(self, *, description:str):
        def get_ai_tool(tool:Callable[[T], None]):
            ti = ToolInfo[T](
                input_type=tool.__annotations__["input"],
                name = tool.__name__,
                description = description,
                tool = tool
            )
            self.tool_info_dict[tool.__name__] = ti
            return tool
        return get_ai_tool

    def __init__(self, openai_handler:Any, user:User):
        self.openai_handler = openai_handler
        self.tool_info_dict = {}
        self.user = user

    def run(self, question:str):
        from webcli2.action_handlers.system import cli_print

        api_key = self.openai_handler.service.get_action_handler_user_config(
            action_handler_name="openai", 
            user=self.user
        ).get("api_key")
        if not api_key:
            content = """api_key must be provide, you can run
%config% set openai
{
    "api_key": "YOUR_OPENAI_API_KEY_HERE"
}
"""
            cli_print(content, mime="text/plain")
            return
        

        client = OpenAI(api_key=api_key)
        tools = []
        for _, ti in self.tool_info_dict.items():
            t = {
                "type": "function",
                "function": {
                    "name": ti.name,
                    "description": ti.description,
                    "parameters": ti.input_type.model_json_schema(),
                    "strict": True
                }
            }
            tools.append(t)

        completion = client.chat.completions.create(
            # model="gpt-3.5-turbo",
            # model="gpt-4",
            model="gpt-4o",
            store=True,
            messages=[
                {"role": "user", "content": question}
            ],
            tools=tools
        )

        for tc in completion.choices[0].message.tool_calls:
            tool = self.tool_info_dict.get(tc.function.name)
            input = tool.input_type.model_validate(json.loads(tc.function.arguments))
            tool.tool(input)
        return completion
    

#######################################################
# Should only be called by custom code in %python% action
#######################################################
def create_ai_agent() -> AIAgent:
    from webcli2.action_handlers.system import get_python_thread_context
    thread_context = get_python_thread_context()
    openai_handler = thread_context.service.get_action_handler("openai")
    return AIAgent(openai_handler, thread_context.user)
