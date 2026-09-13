import os

def create_pull_request(incident_id: str, diff: str) -> str:
    # We mock the GitHub PR creation since we are not pushing to GitHub right now.
    print(f"Mocking GitHub PR creation for incident {incident_id}")
    print(f"Applying diff:\n{diff}")
    print("Branch fix/incident-" + incident_id + " created locally.")
    
    # Return a fake PR URL
    return f"https://github.com/mock-org/mock-repo/pull/{incident_id.replace('inc_', '')}"
