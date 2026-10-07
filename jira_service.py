import requests
from requests.auth import HTTPBasicAuth
from config import JIRA_URL, JIRA_EMAIL, JIRA_API_TOKEN, JIRA_PROJECT_KEY


class JiraService:
    def create_ticket(self, summary, description, priority="High"):
        if not all([JIRA_URL, JIRA_EMAIL, JIRA_API_TOKEN, JIRA_PROJECT_KEY]):
            return {
                "success": False,
                "message": "Jira is not configured. Set JIRA_URL, JIRA_EMAIL, JIRA_API_TOKEN, and JIRA_PROJECT_KEY in .env, then restart the app."
            }

        endpoint = f"{JIRA_URL}/rest/api/3/issue"
        payload = {
            "fields": {
                "project": {"key": JIRA_PROJECT_KEY},
                "summary": summary,
                "description": {
                    "type": "doc",
                    "version": 1,
                    "content": [{
                        "type": "paragraph",
                        "content": [{"text": description, "type": "text"}]
                    }]
                },
                "issuetype": {"name": "Task"},
                "priority": {"name": priority}
            }
        }

        try:
            response = requests.post(
                endpoint,
                json=payload,
                auth=HTTPBasicAuth(JIRA_EMAIL, JIRA_API_TOKEN),
                headers={
                    "Accept": "application/json",
                    "Content-Type": "application/json"
                },
                timeout=20
            )
            if response.status_code in (200, 201):
                data = response.json()
                return {
                    "success": True,
                    "ticket_id": data.get("key"),
                    "message": "Jira support ticket created successfully"
                }
            try:
                error_data = response.json()
                details = "; ".join(error_data.get("errorMessages", []))
                field_errors = error_data.get("errors", {})
                if field_errors:
                    details = "; ".join(
                        filter(None, [details, *(
                            f"{field}: {message}"
                            for field, message in field_errors.items()
                        )])
                    )
            except ValueError:
                details = response.text.strip()

            if response.status_code == 401:
                message = "Jira authentication failed (HTTP 401). Check the Jira account email and API token."
            elif response.status_code == 403:
                message = "Jira denied access (HTTP 403). Check the account's project permissions."
            else:
                message = f"Jira returned HTTP {response.status_code}."
            if details:
                message = f"{message} {details}"
            return {"success": False, "message": message}
        except requests.RequestException as exc:
            return {"success": False, "message": f"Could not reach Jira: {exc}"}
