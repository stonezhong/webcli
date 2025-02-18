# Print Image
Here is an example:
```python
%python%

with open("/Users/shizhong/Desktop/my-picture.png", "rb") as f:
    cli_print(f.read(), mime="image/png")
```