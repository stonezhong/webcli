# Index
* [Command Examples](#command-examples)
    * [Run Python Code](#run-python-code)
    * [Load Code and Run ](#load-code-and-run)
    * [Load Code and Print and Run](#load-code-and-print-and-run)
    * [Save Code and Run](#save-code-and-run)
* [Functions Available](#functions-available)

# Command Examples
## Run Python Code
```python
%python%
print("Hello")
```

## Load Code and Run 
In this example, it prepend the code read from foo.py with your code then run it
```python
%python% --load foo.py
print("Hello")
```

## Load Code and Print and Run
In this example, it prepend the code read from foo.py with your code then run it
```python
%python% --load foo.py --print
print("Hello")
```

## Save Code and Run
In this example, your code will be saved to foo.py, then run it.
```python
%python% --save foo.py
print("Hello")
```

# Functions Available
```python
# Print text or binary content
cli_print(content: Union[str,bytes], mime:str="text/html")
```
