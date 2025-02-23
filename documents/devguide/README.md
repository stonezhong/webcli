# Index
* [Unit Test](#unit-test)
    * [Setup Python Virtual Environment for test](#setup-python-virtual-environment-for-test)
    * [Run Unit Test](#run-unit-test)
* [Component Summary](#component-summary)
* [Coding Style](#coding-style)

# Unit Test
## Setup Python Virtual Environment for test
```bash
# assumign your webcli project root is at ~/projects/webcli
mkdir ~/.venvs/webcli-unit-test
python3 -m venv ~/.venvs/webcli-unit-test
source ~/.venvs/webcli-unit-test/bin/activate
pip install pip setuptools --upgrade
cd ~/projects/webcli
pip install -e .
pip install -r tests/requirements.txt
```

## Run Unit Test
```bash
# assumign your webcli project root is at ~/projects/webcli
source ~/.venvs/webcli-unit-test/bin/activate
cd ~/projects/webcli
pytest -rP
```

# Component Summary
see [Component Summary](components.md)

# Coding Style
* See also [Google Python Style Guide](#https://google.github.io/styleguide/pyguide.html)
