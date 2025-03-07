from typing import List, Any, Optional
import jinja2
from webcli2.core.ai import Task, AgenticMixin, Tool, Message, MessageRole, CompositeTask, cli_print, AIThinker, AIAgentInfo
from pydantic import BaseModel, Field, ConfigDict
from webcli2.core.ai.libs.oracle import OracleTools

class HTMLTableTool(Tool):
    class InputType(BaseModel):
        jinja_template: str = Field(..., description="A Jinja template string for table")
        store_key: str = Field(..., description="The name after storte the result as")
        items_key: str = Field(..., description="The name after pick items from stored value")
        model_config = ConfigDict(extra='forbid')

    def __init__(self):
        super().__init__(name="generate_jinja_template", description="Generate Jinja Template", input_type=self.InputType)

    def run(self, input:InputType):
        return input


class HTMLTableGenerator(Task, AgenticMixin):
    description = """
HTMLTableGenerator
    I can take an array of items and produce an HTML table.
    For example, you can ask: Generate a HTML table, pick items from stored value xyz, the first column name is color, second column name is dimenstion.length, the table does not require header. Store the result as html_table.
"""

    def __init__(self, parent:Task):
        super().__init__(
            name="HTML Table Generator", 
            parent=parent
        )
        self.add_tool(HTMLTableTool())

    def run(self):
        cli_print(f"HTMLTableGenerator: run")
        if not self.has_variable("items_key"):
            sys_prompt1 = """
You can generate a Jinja template for HTML table with the example below, assuming your table has two columns, first column pick value from item.field1, second column pick value from item.field2. You can follow the same patter to generate table with more columns.
Always use the term `items` since this is the variable name we always use.
<table>
    {% for item in items %}
    <tr>
        <td>{{ item.field1 }}</td>
        <td>{{ item.field2 }}</td>
    </tr>
    {% endfor %}
</table>
"""

            sys_prompt2 = """
Instructions:
```
- To generate jinja template, use tool generate_jinja_template.
- Use the provided tool to fetch data.
- When you are asked to generate a HTML table, simply return the jinja template for the table
```
"""
            actual_promot = sys_prompt1 + "\n\n" + self.get_variable("prompt") + "\n" + sys_prompt2
            r, results = self.ask_llm([Message(role=MessageRole.USER, content=actual_promot)])

            result = results["generate_jinja_template"]

            self.set_variable("jinja_template", result.jinja_template)
            self.set_variable("items_key", result.items_key)
            self.set_variable("result_key", result.store_key)

        items_key = self.get_variable("items_key")
        if not self.parent.has_variable(items_key):
            cli_print(f"{items_key} does not exist!", mime="text/plain")
            return
        
        items = self.parent.get_variable(items_key)
        jinja_template = self.get_variable("jinja_template")
        environment = jinja2.Environment()
        template = environment.from_string(jinja_template)
        rendered_template = template.render(items=items)
        self.set_variable("result", rendered_template)
        result_key = self.get_variable("result_key")
        self.parent.set_variable(result_key, rendered_template)
        self.set_finished()
