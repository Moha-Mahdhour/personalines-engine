"""Shared fixtures for pipeline tests."""
from personalines.domain import Task
from personalines.jobs import render_csv
from personalines.status import TaskStatus

LEADS = [
    {"Name": "Jordan", "LinkedIn": "https://linkedin.com/in/jordan"},
    {"Name": "Sam", "LinkedIn": ""},
    {"Name": "Riley", "LinkedIn": "https://linkedin.com/in/riley"},
]
PROFILES = {
    "https://linkedin.com/in/jordan": {"headline": "Head of Operations", "city": "Austin"},
    "https://linkedin.com/in/riley": {"headline": "Robotics Engineer", "summary": "Builds warehouse robots."},
}


def task(status=TaskStatus.INIT, file_name="leads.csv", field="LinkedIn", task_id=1):
    return Task(id=task_id, user_id="u-1", file_name=file_name, status=status, linkedin_field=field)


def leads_csv(rows=LEADS):
    return render_csv(rows)
