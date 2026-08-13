"""Phase 0 hello-world: list Google Tasks task lists.

Run:  python -m src.integrations.google_tasks
Shares OAuth credentials/token with google_calendar.py (same Google Cloud project).
"""

from googleapiclient.discovery import build

from src.integrations.google_auth import get_credentials


def list_task_lists() -> list[dict]:
    creds = get_credentials()
    service = build("tasks", "v1", credentials=creds)
    result = service.tasklists().list(maxResults=10).execute()
    return result.get("items", [])


if __name__ == "__main__":
    task_lists = list_task_lists()
    if not task_lists:
        print("No task lists found.")
    for task_list in task_lists:
        print(f"{task_list['id']} — {task_list['title']}")
