from jira import JIRA
import requests
import json
import os
from webcli2.action_handlers.system import get_python_thread_context
from webcli2.config import load_config

class OracleTools:
    jira_personal_access_token: str
    confluence_personal_access_token: str

    def __init__(self):
        config = load_config()
        thread_context = get_python_thread_context()

        user = thread_context.user
        config_filename = os.path.join(config.core.users_home_dir, str(user.id), ".ai-agent.json")
        with open(config_filename, "rt") as f:
            ai_agent_cfg = json.load(f)
            self.jira_personal_access_token = ai_agent_cfg["JIRA_PERSONAL_ACCESS_TOKEN"]
            self.confluence_personal_access_token = ai_agent_cfg["CONFLUENCE_PERSONAL_ACCESS_TOKEN"]

    def jira_execute_jql(self, query:str):
        options = {"server": "https://jira.oci.oraclecorp.com"}
        jira_client = JIRA(options, token_auth=self.jira_personal_access_token)
        issues = jira_client.search_issues(query, maxResults=100)
        return issues

    # see https://developer.atlassian.com/cloud/confluence/rest/v2/api-group-page/#api-pages-get
    def get_confluence_page(self, page_id:str):
        headers = {
            'Authorization': f'Bearer {self.confluence_personal_access_token}',
            "Accept": "application/json",
        }
        r = requests.get(
            f'https://confluence.oraclecorp.com/confluence/rest/api/content/{page_id}?expand=body.storage&include-version=true&', 
            headers=headers
        )
        # page body is in response.body.storage.value
        return r.json()

    def get_confluence_page_info(self, page_id:str):
        headers = {
            'Authorization': f'Bearer {self.confluence_personal_access_token}',
            "Accept": "application/json",
        }
        r = requests.get(
            f'https://confluence.oraclecorp.com/confluence/rest/api/content/{page_id}', 
            headers=headers
        )
        # page body is in response.body.storage.value
        return r.json()

    def update_confluence_page(self, page_id:str, *, title:str, content:str):
        # first, let's get the version
        page_info = self.get_confluence_page_info(page_id)
        version_number = page_info["version"]["number"]
        headers = {
            'Authorization': f'Bearer {self.confluence_personal_access_token}',
            'Content-Type': 'application/json',
            "Accept": "application/json",
        }
        payload = {
            "id": page_id,
            "type":"page",
            "title": title,
            "space":{
                "key":"HWD"
            },
            "body":{
                "storage":{
                    "value": content,
                    "representation":"storage"
                }
            },
            "version": {
            "number": version_number + 1,
            "message": "Updated via API"
            }
        }
        r = requests.put(
            f'https://confluence.oraclecorp.com/confluence/rest/api/content/{page_id}', 
            headers=headers, 
            json=payload
        )

