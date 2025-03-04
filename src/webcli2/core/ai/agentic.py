import logging
logger = logging.getLogger(__name__)

from typing import List, Dict, Any, Optional, TypeVar, Type
import enum
from abc import ABC, abstractmethod
import json
from pydantic import BaseModel
from openai import OpenAI

class AgentError(Exception):
    pass

class VariableMissing(AgentError):
    """A task failed to provide a variable it has promised.
    """
    variable_name: str

    def __init__(self, variable_name, *argc, **kwargs):
        super().__init__(*argc, **kwargs)
        self.variable_name = variable_name

class InvalidVariableMap(AgentError):
    """A child task's variable map is not 1:1 map.
    """
    pass

class ToolNotFound(AgentError):
    """LLM returned a function call which we never registered.
    """
    tool_name: str

    def __init__(self, tool_name:str, *argc, **kwargs):
        super().__init__(*argc, **kwargs)
        self.tool_name = tool_name

class MissingOpenAIAPIKey(AgentError):
    """Cannot call OpenAI since missing API Key.
    """
    pass

class DuplicateTool(AgentError):
    """An AI Agent is trying to register two tool with the same name.
    """
    tool_name: str

    def __init__(self, tool_name:str, *argc, **kwargs):
        super().__init__(*argc, **kwargs)
        self.tool_name = tool_name

class Task(ABC):
    name: str
    description: str
    requires: List[str]
    provides: List[str]
    variables: Dict[str, Any]

    def __init__(self, *, name:str, description:str, requires:List[str]=[], provides:List[str]=[]):
        super().__init__()
        self.name = name
        self.description = description
        self.requires = requires.copy()
        self.provides = provides.copy()
        self.variables = {}

    def set_variable(self, name:str, value:Any):
        self.variables[name] = value
    
    def get_variable(self, name:str) -> Any:
        if name not in self.variables:
            raise VariableMissing(name)
        return self.variables[name]

    def has_variable(self, name:str) -> bool:
        return name in self.variables

    @abstractmethod
    def run(self):
        pass

class _TaskWrapper:
    task: Task
    variable_map: Optional[Dict[str, str]] # key is the variable name in context, value is the variable name in task
    _invert_variable_map: Optional[Dict[str, str]] # invert of variable_map
    finished: bool

    ###############################################################################################################
    # a task may require ["x", "y"]
    # variable_map = {"a": "x", "b": "y"} means the task will take variable "a" from it's parent as "x"
    # and "b" from it's parent as "y"
    ###############################################################################################################

    def __init__(self, task:Task, variable_map:Optional[Dict[str, str]]=None):
        self.task = task
        self.finished = False
        if variable_map is None:
            self.variable_map = None
            self._invert_variable_map = None
        else:
            self.variable_map = variable_map.copy()
            self._invert_variable_map = {}
            for k, v in variable_map.items():
                if v in self._invert_variable_map:
                    raise InvalidVariableMap()
                self._invert_variable_map[v] = k
    
class CompositeTask(Task):
    children:List[_TaskWrapper]            # child tasks wrapped

    def __init__(self, *, name:str, description:str, requires:List[str]=[], provides:List[str]=[]):
        super().__init__(name=name, description=description, requires=requires, provides=provides)
        self.children = []

    def add_task(self, child:Task, *, variable_map:Optional[Dict[str, str]]=None):
        self.children.append(_TaskWrapper(child, variable_map))
    
    def can_run_task(self, task_wrapper:_TaskWrapper) -> bool:
        required_variable_names = [
            task_wrapper._invert_variable_map(variable_name) for variable_name in task_wrapper.task.requires
        ]
        for required_variable_name in required_variable_names:
            if not self.has_variable(required_variable_name):
                return False
        return True

    def run_task(self, task_wrapper:_TaskWrapper):
        required_variable_names = [
            task_wrapper._invert_variable_map(variable_name) for variable_name in task_wrapper.task.requires
        ]
        task_wrapper.finished = True
        # import variable into task before run
        for required_variable_name in required_variable_names:
            task_wrapper.task.set_variable(
                task_wrapper.variable_map[required_variable_name],
                self.get_variable(required_variable_name)
            )
        # run task
        task_wrapper.task.run()
        # export variable from task after run
        for variable_name in task_wrapper.task.provides:
            value = task_wrapper.task.get_variable(variable_name)
            self.set_variable(
                task_wrapper._invert_variable_map[variable_name],
                value
            )

    def run(self):
        ###################################################################
        # - If a child can run, we will run it
        # - If non of the child can run, we will stop
        ###################################################################
        while True:
            task_finished = 0
            for task_wrapper in self.children:
                if task_wrapper.finished:
                    continue
                if self.can_run_task(task_wrapper):
                    self.run_task(task_wrapper)
                    task_finished += 1
            if task_finished == 0:
                break


T = TypeVar('T', bound=BaseModel)
    
class Tool(ABC):
    name: str
    description: str
    input_type: Type[T]

    def __init__(self, *, name:str, description:str, input_type:Type[T]):
        super().__init__()
        self.name = name
        self.description = description
        self.input_type = input_type
    
    @abstractmethod
    def run(self, input:T):
        pass


class MessageRole(enum.Enum):
    SYSTEM = "system"
    USER = "user"
    ASSISTANT = "assistant"

class Message(BaseModel):
    role:MessageRole
    content:str

class LLMModel(enum.Enum):
    GPT_4O = "gpt-4o"
    GPT_35_TURBO = "gpt-3.5-turbo"
    GPT_4 = "gpt-4"

class AgenticMixin:
    tools: Dict[str, Tool]

    def __init__(self):
        super().__init__()
        self.tools = {}
    
    def add_tool(self, tool:Tool):
        if tool.name in self.tools:
            raise DuplicateTool(tool.name)
        self.tools[tool.name] = tool
    
    def ask_llm(self, messages: List[Message], *, model=LLMModel.GPT_4O):

        from webcli2.action_handlers.system import get_python_thread_context
        thread_context = get_python_thread_context()
        user = thread_context.user
        openai_handler = thread_context.service.get_action_handler("openai")
        api_key = openai_handler.service.get_action_handler_user_config(
            action_handler_name="openai", 
            user=user
        ).get("api_key")
        if api_key is None:
            raise MissingOpenAIAPIKey()
        
        openai_client = OpenAI(api_key=api_key)


        tools = []
        for _, tool in self.tools.items():
            t = {
                "type": "function",
                "function": {
                    "name": tool.name,
                    "description": tool.description,
                    "parameters": tool.input_type.model_json_schema(),
                    "strict": True
                }
            }
            tools.append(t)

        completion = openai_client.chat.completions.create(
            model=model.value,
            store=True,
            messages = [
                message.model_dump(mode='json') for message in messages
            ],
            tools=tools
        )

        for tc in completion.choices[0].message.tool_calls:
            tool = self.tools.get(tc.function.name)
            if tool is None:
                raise ToolNotFound(tc.function.name)
            input = tool.input_type.model_validate(json.loads(tc.function.arguments))
            logger.debug(f"Invoking tool [{tc.function.name}] with argument [{input}]")
            tool.run(input)
        return completion
