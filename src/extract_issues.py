import requests
import pandas as pd
import os

# Replace with your personal access token and repository details
GITHUB_TOKEN = os.getenv("GITHUB_TOKEN")
REPO_OWNER = 'edwardpiwowar'
REPO_NAME = 'BBA'
API_URL = f'https://api.github.com/repos/{REPO_OWNER}/{REPO_NAME}/issues'

if not GITHUB_TOKEN:
    raise ValueError("GitHub token not found. Please set it as an environment variable.")

# Headers for the request
headers = {
    'Authorization': f'token {GITHUB_TOKEN}',
    'Accept': 'application/vnd.github.v3+json'
}

# Parameters to fetch all issues (including pagination)
params = {
    'state': 'all',
    'per_page': 100,
    'page': 1
}

# List to hold all issues
all_issues = []

while True:
    response = requests.get(API_URL, headers=headers, params=params)
    response.raise_for_status()
    issues = response.json()
    if not issues:
        break
    all_issues.extend(issues)
    params['page'] += 1

# Extract relevant fields
issues_data = [{
    'id': issue['id'],
    'number': issue['number'],
    'title': issue['title'],
    'state': issue['state'],
    'created_at': issue['created_at'],
    'updated_at': issue['updated_at'],
    'closed_at': issue['closed_at'],
    'user': issue['user']['login'],
    'assignee': issue['assignee']['login'] if issue['assignee'] else None,
    'labels': ', '.join(label['name'] for label in issue['labels']),
    'body': issue['body']
} for issue in all_issues]

# Create a DataFrame and export to CSV
df = pd.DataFrame(issues_data)
df.to_csv('github_issues.csv', index=False)

print(f"Exported {len(all_issues)} issues to github_issues.csv")
