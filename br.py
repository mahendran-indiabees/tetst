import os
import requests
import sys
import json

GITHUB_API_URL = "https://api.github.com"
GITHUB_TOKEN = os.getenv("GITHUB_TOKEN")
REPO = os.getenv("REPO")
HEADERS = {
    "Authorization": f"token {GITHUB_TOKEN}",
    "Accept": "application/vnd.github.v3+json"
}

# Store original protection state globally
ORIGINAL_PROTECTION = None

def get_protection_settings(branch):
    """Get full branch protection settings"""
    url = f"{GITHUB_API_URL}/repos/{REPO}/branches/{branch}/protection"
    response = requests.get(url, headers=HEADERS)
    return response.json() if response.status_code == 200 else None

def update_protection(branch, data):
    """Update branch protection with full settings"""
    url = f"{GITHUB_API_URL}/repos/{REPO}/branches/{branch}/protection"
    response = requests.put(url, headers=HEADERS, json=data)
    response.raise_for_status()

def modify_protection(action, user_id_or_setting):
    global ORIGINAL_PROTECTION
    
    branch = get_default_branch()
    current_protection = get_protection_settings(branch)
    
    if not current_protection:
        print("No branch protection rules found")
        return

    if action == "BYPASS":
        # Store original state
        ORIGINAL_PROTECTION = current_protection.copy()
        
        # Modify bypass settings
        bypass_users = current_protection.get(
            "required_pull_request_reviews", {}
        ).get("bypass_pull_request_allowances", {}).get("users", [])
        
        # Add user if not present
        if user_id_or_setting not in bypass_users:
            bypass_users.append(user_id_or_setting)
        
        # Disable enforce_admins temporarily
        updated_protection = current_protection.copy()
        updated_protection.update({
            "required_pull_request_reviews": {
                **current_protection.get("required_pull_request_reviews", {}),
                "bypass_pull_request_allowances": {
                    "users": bypass_users,
                    "teams": current_protection.get(
                        "required_pull_request_reviews", {}
                    ).get("bypass_pull_request_allowances", {}).get("teams", []),
                    "apps": current_protection.get(
                        "required_pull_request_reviews", {}
                    ).get("bypass_pull_request_allowances", {}).get("apps", [])
                }
            },
            "enforce_admins": False
        })
        
        update_protection(branch, updated_protection)
        print("::set-output name=original_enforce_admins::" + 
              str(ORIGINAL_PROTECTION.get("enforce_admins", False)))

    elif action == "RESTORE":
        if not ORIGINAL_PROTECTION:
            print("No original protection state stored")
            return
            
        # Restore original settings
        update_protection(branch, ORIGINAL_PROTECTION)
        print("Protection rules restored successfully")

if __name__ == "__main__":
    if len(sys.argv) < 3:
        print("Usage: python script.py [BYPASS|RESTORE] [USER_ID|SETTING]")
        sys.exit(1)
    
    modify_protection(sys.argv[1], sys.argv[2])
