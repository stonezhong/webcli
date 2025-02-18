import logging
logger = logging.getLogger(__name__)

from typing import Any, List, Dict, TypeVar, Generic, Type
from abc import ABC, abstractmethod
from pydantic import BaseModel
import json
from openai import OpenAI

from webcli2.core.data import User

T = TypeVar('T', bound=BaseModel)

class AITool(ABC, Generic[T]):
    name:str
    description:str
    input_type: Type[T]

    def __init__(self, *, name:str, description:str, input_type:Type[T]):
        self.name = name
        self.description = description
        self.input_type = input_type

    @abstractmethod
    def invoke(self, input:T):
        pass

class AIAgent:
    tools: List[dict]
    user: User
    openai_handler:Any

    def __init__(self, openai_handler:Any, user:User):
        self.openai_handler = openai_handler
        self.tools = []
        self.tool_dict: Dict[str, AITool] = {} # key is the tool name, value is AITool
        self.user = user

    # Register a AI Tool
    def register_tool(self, tool:AITool):
        t = {
            "type": "function",
            "function": {
                "name": tool.name,
                "description": tool.description,
                "parameters": tool.input_type.model_json_schema(),
                "strict": True
            }
        }
        self.tools.append(t)
        self.tool_dict[tool.name] = tool

    def ask_ai(self, question:str):
        from webcli2.action_handlers.openai.main import cli_print

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
            raise ValueError("No API KEY for openai SDK")

        client = OpenAI(api_key=api_key)
        completion = client.chat.completions.create(
            # model="gpt-3.5-turbo",
            # model="gpt-4",
            model="gpt-4o",
            store=True,
            messages=[
                {"role": "user", "content": question}
            ],
            tools=self.tools
        )
        return completion
    
    def process_tools_response(self, completion):
        for tc in completion.choices[0].message.tool_calls:
            ai_tool = self.tool_dict.get(tc.function.name)
            if ai_tool is None:
                continue
            input = ai_tool.input_type.model_validate(json.loads(tc.function.arguments))
            ai_tool.invoke(input)
