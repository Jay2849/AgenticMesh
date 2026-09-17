import os
from github import Github

def create_pull_request(incident_id: str, diff: str) -> str:
    token = os.getenv("GITHUB_TOKEN")
    if not token:
        print(f"No GITHUB_TOKEN provided. Mocking PR creation for incident {incident_id}")
        return f"https://github.com/mock-org/mock-repo/pull/{incident_id.replace('inc_', '')}"
        
    try:
        g = Github(token)
        repo_name = os.getenv("GITHUB_REPO", "mock-org/mock-repo")
        repo = g.get_repo(repo_name)
        
        branch_name = f"fix/incident-{incident_id}"
        sb = repo.get_branch("main")
        repo.create_git_ref(ref=f"refs/heads/{branch_name}", sha=sb.commit.sha)
        
        pr = repo.create_pull(
            title=f"Fix for incident {incident_id}",
            body=f"Automated PR for incident {incident_id}.\n\nDiff:\n```diff\n{diff}\n```",
            head=branch_name,
            base="main"
        )
        print(f"Created real GitHub PR: {pr.html_url}")
        return pr.html_url
    except Exception as e:
        print(f"GitHub API Error: {e}. Falling back to mock PR.")
        return f"https://github.com/mock-org/mock-repo/pull/{incident_id.replace('inc_', '')}"
