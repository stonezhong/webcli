import logging
logger = logging.getLogger(__name__)

from typing import List, Dict, Any, Optional, TypeVar, Type, Generic, Tuple, Callable
import enum
from abc import ABC, abstractmethod
import json
from pydantic import BaseModel, Field, ConfigDict
from openai import OpenAI, ChatCompletion
from webcli2.action_handlers.system import cli_print

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

class AgentClassNotFound(AgentError):
    """We cannot create a instance of a agent class
    """
    agent_class_name: str

    def __init__(self, agent_class_name:str, *argc, **kwargs):
        super().__init__(*argc, **kwargs)
        self.agent_class_name = agent_class_name

################################################################
# A task can optionally have parent task
# You can run a task, as long as it is not finished
# In some cases a task depend on parent's variable, once that
# variable is not yet provided, run the task returns immediately
################################################################
class Task(ABC):
    parent: Optional["Task"]
    name: str
    description: str = ""
    _variables: Dict[str, Any]
    _finished: bool

    def __init__(self, *, name:str, parent:Optional["Task"]=None):
        super().__init__()
        self.parent = parent
        self.name = name
        self._variables = {}
        self._finished = False

    def set_finished(self):
        self._finished = True
    
    def is_finished(self):
        return self._finished
    
    def set_variable(self, name:str, value:Any):
        self._variables[name] = value
    
    def get_variable(self, name:str) -> Any:
        if name not in self._variables:
            raise VariableMissing(name)
        return self._variables[name]

    def has_variable(self, name:str) -> bool:
        return name in self._variables

    @abstractmethod
    def run(self):
        pass

class CompositeTask(Task):
    children:List[Task]            # child tasks wrapped

    def __init__(self, *, name:str):
        super().__init__(name=name)
        self.children = []

    def add_task(self, child:Task):
        child.parent = self
        self.children.append(child)
    
    def run(self):
        ###################################################################
        # - If a child can run, we will run it
        # - If non of the child can run, we will stop
        ###################################################################
        while True:
            task_finished = 0
            for task in self.children:
                if task.is_finished():
                    continue
                logger.info(f"CompositeTask.run: task={task.name}")
                task.run()
                task_finished += 1
            if task_finished == 0:
                break
        
        has_unfinished_task = False
        for task in self.children:
            if not task.is_finished():
                has_unfinished_task = True
                break
        if not has_unfinished_task:
            self.set_finished()



T = TypeVar('T', bound=BaseModel)
    
class Tool(Generic[T], ABC):
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
    
    def add_tool(self, tool:Tool[T]):
        if tool.name in self.tools:
            raise DuplicateTool(tool.name)
        self.tools[tool.name] = tool

    def ask_llm(self, messages: List[Message], *, model=LLMModel.GPT_4O, temperature=0.0) -> Tuple[ChatCompletion, Dict[str, Any]]:
        """Ask LLM, invoke tools
        Retruns:
            A tuple, first element is the LLM response, 2nd element is the tool invocation result
        """

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
            temperature=temperature,
            tools=tools
        )

        results = {}

        for tc in completion.choices[0].message.tool_calls:
            tool = self.tools.get(tc.function.name)
            if tool is None:
                raise ToolNotFound(tc.function.name)
            input = tool.input_type.model_validate(json.loads(tc.function.arguments))
            logger.debug(f"Invoking tool [{tc.function.name}] with argument [{input}]")
            result = tool.run(input)
            results[tc.function.name] = result
        return completion, results

class AIPlannerTool(Tool):
    class InputType(BaseModel):
        class AgentInfo(BaseModel):
            agent_name: str = Field(..., description="The name of the AI agent.")
            question: str = Field(..., description="The Question passed to the AI Agent")
            model_config = ConfigDict(extra='forbid')

        plans: List[AgentInfo] = Field(..., description="List of agent info, which contains agent name and question passed to agent.")
        model_config = ConfigDict(extra='forbid')

    def __init__(self):
        super().__init__(name="discover_ai_agents", description="Discover AI Agents", input_type=self.InputType)

    def run(self, input:InputType):
        return input

Q = TypeVar('Q', bound='Task')

class AIAgentInfo(Generic[Q]):
    name:str
    description:str
    factory: Callable[[], Q]

    def __init__(self, name:str, description:str, factory:Callable[[], Q]):
        self.name = name
        self.description = description
        self.factory = factory
    
    @classmethod
    def from_class(cls, klass: Type[Q]):
        return AIAgentInfo(klass.__name__, klass.description, klass)


class AIThinker(CompositeTask, AgenticMixin):
    ai_agents_info:List[AIAgentInfo[Task]]

    def __init__(self, *argc, **kwargs):
        super().__init__(*argc, **kwargs)
        self.add_tool(AIPlannerTool())
        self.ai_agents_info = []

    def add_agent_factory(self, ai_agent_info:AIAgentInfo):
        self.ai_agents_info.append(ai_agent_info)
    
    def create_agent(self, agent_class_name:str)->Task:
        for ai_agent_info in self.ai_agents_info:
            if agent_class_name == ai_agent_info.name:
                agent = ai_agent_info.factory(parent=self)
                return agent
        raise AgentClassNotFound(agent_class_name)
    
    def create_agent_descriptions(self):
        p = "I have the following AI Agent:\n"
        p += "```\n"
        for ai_agent_info in self.ai_agents_info:
            p += (ai_agent_info.description + "\n")
        p += "```\n"
        p += "Could you please let me know which AI agent I shall use as next steps? Also figure out the respective question for each of the picked AI agent."
        return p
    

    def run(self):
        # Let's plan first
        prompt = self.get_variable("prompt")
        prompt += f"\n\n{self.create_agent_descriptions()}"
        logger.info(f"AIThinker.run: ask LLM with following message")
        logger.info(prompt)
        logger.info(f"AIThinker.run: ask LLM =====")
        r, results = self.ask_llm(
            [
                Message(role=MessageRole.USER, content=prompt)
            ]
        )
        discover_ai_agents:AIPlannerTool.InputType = results["discover_ai_agents"]
        for plan in discover_ai_agents.plans:
            agent = self.create_agent(plan.agent_name)
            agent.set_variable("prompt", plan.question)
            self.add_task(agent)

        super().run()        
