from fastapi.responses import HTMLResponse

##########################################################
# Generate a HTMLResponse that redirect user to given URL
##########################################################
def redirect(url) -> HTMLResponse:
    html_content = f"""<!DOCTYPE html>
<html xmlns="http://www.w3.org/1999/xhtml">
<head>
    <meta content="text/html; charset=utf-8" http-equiv="Content-Type"/>
    <meta http-equiv="refresh" content="0;url={url}">
</head>
<body></body>
</html>
"""
    return HTMLResponse(content=html_content)
