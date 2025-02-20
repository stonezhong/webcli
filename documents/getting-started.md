# Index
* [Setup WebCLI to run python code](#setup-ai-lab)
  * [Step 1: Create python virtual environment, install necessary python packages](#step-1-create-python-virtual-environment-install-necessary-python-packages)
  * [Step 2: Create config](#step-2-create-config)

# Setup WebCLI to run python code
This tool requires python 3.13, I have pyenv installed so I can invoke python 3.13 this way
```bash
$PYENV_ROOT/versions/3.13.0/bin/python
```

## Step 1: Create python virtual environment, install necessary python packages
```bash
mkdir ~/ailab
mkdir ~/ailab/.venv
$PYENV_ROOT/versions/3.13.0/bin/python -m venv ~/ailab/.venv
source ~/ailab/.venv/bin/activate
pip install pip setuptools --upgrade
pip install webcli2
pip install openai
```

## Step 2: Create config

Create a file `~/ailab/logcfg.yaml`, with the following content:
```yaml
version: 1
disable_existing_loggers: False
formatters:
  standard:
    format: "%(asctime)s - %(process)d - %(name)s - %(levelname)s - %(message)s"
handlers:
  fileHandler:
    class: logging.handlers.TimedRotatingFileHandler
    level: DEBUG
    formatter: standard
    filename: webcli.log
    interval: 1
    backupCount: 7
    when: midnight
loggers:
  oci._vendor.urllib3.connectionpool:
    handlers: [fileHandler]
    level: WARNING
    propagate: False
  uvicorn.error:
    handlers: [fileHandler]
    level: WARNING
    propagate: False
  uvicorn.access:
    handlers: [fileHandler]
    level: WARNING
    propagate: False
  httpcore.http11:
    handlers: [fileHandler]
    level: WARNING
    propagate: False
  httpcore.connection:
    handlers: [fileHandler]
    level: WARNING
    propagate: False
  openai._base_client:
    handlers: [fileHandler]
    level: WARNING
    propagate: False
  oci.circuit_breaker:
    handlers: [fileHandler]
    level: WARNING
    propagate: False
root:
  level: DEBUG
  handlers: [fileHandler]
```

Then create a file `~/ailab/webcli_cfg.yaml` with the following content:
Note, you may need to modify db_url if based on your user home directory.
```yaml
core:
  log_config_filename: logcfg.yaml
  websocket_uri: ws://localhost:8000/ws
  db_url: sqlite:////home/stonezhong/ailab/webcli.db
  resource_dir: ~/ailab/resources
  users_home_dir: ~/ailab/users
  action_handlers:
    system:
      module_name: webcli2.action_handlers.system
      class_name: SystemActionHandler
    openai:
      module_name: webcli2.action_handlers.openai
      class_name: OpenAIActionHandler
  private_key: |-
    -----BEGIN PRIVATE KEY-----
    MIIEvAIBADANBgkqhkiG9w0BAQEFAASCBKYwggSiAgEAAoIBAQCT2NOiinxmnYEZ
    mlovwPNzvl5bZSBz015kJ6I+VsdM/A56QwZTMFktY0TX58Xw0ATzqwvRNzdtCQfG
    nvuUHjl6Wnv2333USTkqFmB5Y72sA6o6i4N0vtIlCgG6XnI5Cn75pVRnCOjf2GlT
    BeAcs7RFhc45+2xCubmQ75TRpbPQ3MMH+VBKpQcnHp+MVpM6tsWvOtnteYZ6cCN1
    vn0S6OorKV35dCVs5YirhAeCZoD/GdATTdLueRIbRWYpZv3GHGlDcxkm8enbVZqu
    890AvIUnnelByeR6hicEC4SVz8xKUtcgYWe60BHx8uhDMD1GNNmwhziZWkPBE3Hv
    FB/KfG+/AgMBAAECggEAMZPVkB1hTuXFK2k7keThnm/5Yyt7oOuBrRMvUDk4VuP1
    FOGR5uaBGPu/U6k4kqKm7nDuowchknIjReL9GPOzsYhTJntWThAJ18euLTaZnWuT
    M1OiTs1IWbxLzQurwN34q01aCr0NnjaLRxhiyS0np+KRP5dEe/GcvPHiFRU8Qa6r
    SUfm3g7yY2S6M6pPp9S3NOOeAx9MkYusKZhKpeH8ZDuODFwUcdoKO+YTkf9+1b/N
    T1kaJY1NDvtlGTFXnv2NncJKIDcRI81e4T8BkXy7DnssbNfoo0fvCp+NqV/0eGh2
    23sl4ociZoG6QV+AnG4mvTHVIC0/6V/3HA1IEu4iPQKBgQDE7Ejm61wy3UNYW3uB
    DrAU/y3pTWjHp6PIQ499IdbABrq0N8KEy+SBM+gxfJYDEglDTKMIg1PYwu253rS0
    2uYCBurKSGpExXd7KFy0Bia+osA7Jekk3iCCGMy1C9XRqYy/MTCXDHEetEgw9mOs
    gwJMuGVF0tjkJ9hTkvuXhmY9WwKBgQDAM39Afb4RvOGgJfDPS2XazAJ9+xFuMrG6
    /59bApDfDrC+V09EZ/c/vkpCgdan87tj/2XaZh6bL5nvslMsrCHXhYBt026f+pv9
    odaefflrOY8+dHOZcP+jPyUQQrUtWTjF3QG/7Zg18Lgb7VKM3GWHmdipdqp4KhjQ
    I0ew5n3wbQKBgCCie+5xAOWZD6kb+BrKQVopdAVfA8dau+TbdXMqYXmPY++r8fuq
    AqN647cXy5CUs55InBg0E3gvzc/o3Y+/WzDozo5Zc+sTwppRdROMlW0wcaUbwkiO
    21pUG9DBNl05uQ6Sa1gNAs4w2Gns21XinEX0pSvuJm2hQNOQ30scReNTAoGAVHNM
    Ko4Vgb24daG2GZ9LdcPGJIy4r+7eYQgIgPizpw7RYhEC50+3N+7ouihKpSlW4S1L
    F5dfQ1i7DrMQEMThac1jDN6l8O0wtVTy9FjtystTwWFxma4o5RXNt0NYUECvzWC6
    cBZ5ltnaS4sPho0gn2Bd7rgRVxNIK8wUqAnetFECgYAZFZJrkQ5VP2hybRRMXIjG
    ZUDqKnGwM5hmFe97yP1KD7Iq/X5bYCfWmulUybRciO/Y47YwCl6H/u2qe+Ua6DHi
    twQC1nnUmjAciFffH0gsS3wAG58dZAItexIDV3cIskO2wMjpe4h9blrdiI6+7PGL
    H6OBEK1PSf07i6NF83CW2w==
    -----END PRIVATE KEY-----
  public_key: |-
    -----BEGIN PUBLIC KEY-----
    MIIBIjANBgkqhkiG9w0BAQEFAAOCAQ8AMIIBCgKCAQEAk9jToop8Zp2BGZpaL8Dz
    c75eW2Ugc9NeZCeiPlbHTPwOekMGUzBZLWNE1+fF8NAE86sL0Tc3bQkHxp77lB45
    elp79t991Ek5KhZgeWO9rAOqOouDdL7SJQoBul5yOQp++aVUZwjo39hpUwXgHLO0
    RYXOOftsQrm5kO+U0aWz0NzDB/lQSqUHJx6fjFaTOrbFrzrZ7XmGenAjdb59Eujq
    Kyld+XQlbOWIq4QHgmaA/xnQE03S7nkSG0VmKWb9xhxpQ3MZJvHp21WarvPdALyF
    J53pQcnkeoYnBAuElc/MSlLXIGFnutAR8fLoQzA9RjTZsIc4mVpDwRNx7xQfynxv
    vwIDAQAB
    -----END PUBLIC KEY-----
```

## Step 3: Initialize

Now create some directories:
```bash
mkdir ~/ailab/logs          # directory for logs
mkdir ~/ailab/users         # directory for users
mkdir ~/ailab/resources     # directory for storing binary resources
```

Now set environment variable
```bash
export WEBCLI_HOME=~/ailab
```

Now initialize database,do
```bash
webcli init-db
```

Now create first user account
```bash
webcli create-user --email xyz@abc.com
# enter password
```

Now let's start server
```bash
webcli start
```

Let's do a test, open your browser, open http://localhost:8000/threads
* Click "Create New Thread" button to create a new thread
* When the newly created thread shows up -- it's default title is `no title`, click "Open" button
* In the text area at the bottom of the page type following text and click "Submit" button
```python
%python%
print("Hello")
```

You will see "Hello" gets printed on the page, if you see that, your setup is successful.

# Experiment with AI Agent
Please checkout examples [here](howtos/ai-agent.md) to run AI Agent.
