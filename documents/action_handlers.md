# Index
* [Action Handlers](#action-handlers)
    * [OpenAI](#openai)
        * [Run Python Code](#run-python-code)

# Action Handlers
## OpenAI
### Run Python Code
You can run python code with this action handler.
```python
%python%
<Your Python Code Here>
```

Functions that are available for your python code to call
* `cli_print`
* `run_pyspark_python`
* `run_pyspark_bash`

```python
def do_cli_print(
    content:Union[str, bytes, io.StringIO, io.BytesIO], 
    mime:str=MIMEType.HTML, 
    name:Optional[str]=None
):
    pass
def run_pyspark_python(*, server_id:str, source_code:str) -> str:
    pass

def run_pyspark_bash(*, server_id:str, source_code:str) -> str:
    pass

```
Examples
```
# Print rich format data
from webcli2.webcli import MIMEType
with open("/tmp/profits2024.png", "rb") as image_f:
    image = image_f.read()

cli_print("<h1>Here is the chart</h1>")
cli_print(image, mime=MIMEType.PNG)
cli_print("# Hello", mime=MIMEType.MARKDOWN)
cli_print("Hello", mime=MIMEType.TEXT)
cli_print({"x": 1}, mime=MIMEType.JSON)
```
