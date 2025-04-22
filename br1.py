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

def get_default_branch():
    """Get default branch using simple REST API"""
    url = f"{GITHUB_API_URL}/repos/{REPO}"
    response = requests.get(url, headers=HEADERS)
    response.raise_for_status()
    return response.json()["default_branch"]

def get_branch_protection(branch):
    """Get branch protection settings using REST API"""
    url = f"{GITHUB_API_URL}/repos/{REPO}/branches/{branch}/protection"
    response = requests.get(url, headers=HEADERS)
    if response.status_code == 404:
        return None
    response.raise_for_status()
    return response.json()

def modify_protection(action, user_id_or_setting):
    """Modify branch protection based on action"""
    branch = get_default_branch()
    protection = get_branch_protection(branch)
    
    if not protection:
        print("No branch protection rules found")
        return
    
    if action == "BYPASS":
        user_id = user_id_or_setting
        bypass_users = protection.get("required_pull_request_reviews", {}).get(
            "bypass_pull_request_allowances", {}).get("users", [])
        
        # Check if PR reviews are required
        if not protection.get("required_pull_request_reviews"):
            print("PR reviews not required in protection rules")
            return
        
        # Get current "Do not allow bypass" setting (enforce_admins)
        enforce_admins = protection.get("enforce_admins", {}).get("enabled", False)
        print(f"::set-env name=DO_NOT_ALLOW_BYPASS_SETTINGS::{str(enforce_admins).lower()}")
        
        # Prepare updated protection
        updated_protection = {
            "required_pull_request_reviews": {
                "dismiss_stale_reviews": protection["required_pull_request_reviews"].get("dismiss_stale_reviews", False),
                "require_code_owner_reviews": protection["required_pull_request_reviews"].get("require_code_owner_reviews", False),
                "required_approving_review_count": protection["required_pull_request_reviews"].get("required_approving_review_count", 1),
                "bypass_pull_request_allowances": {
                    "users": list(set(bypass_users + [user_id])),
                    "teams": protection["required_pull_request_reviews"].get(
                        "bypass_pull_request_allowances", {}).get("teams", []),
                    "apps": protection["required_pull_request_reviews"].get(
                        "bypass_pull_request_allowances", {}).get("apps", [])
                }
            },
            "enforce_admins": False  # Always disable during bypass
        }
        
        # Update protection
        url = f"{GITHUB_API_URL}/repos/{REPO}/branches/{branch}/protection"
        response = requests.put(url, headers=HEADERS, json=updated_protection)
        response.raise_for_status()
        print("Successfully modified branch protection for push")
    
    elif action == "RESTORE":
        original_setting = user_id_or_setting.lower() == "true"
        protection = get_branch_protection(branch)
        
        if not protection:
            return
        
        # Get current bypass users
        bypass_users = protection.get("required_pull_request_reviews", {}).get(
            "bypass_pull_request_allowances", {}).get("users", [])
        
        # Remove our user ID if it exists
        if sys.argv[1] == "BYPASS" and sys.argv[2] in bypass_users:
            bypass_users.remove(sys.argv[2])
        
        # Prepare restored protection
        restored_protection = {
            "required_pull_request_reviews": {
                "dismiss_stale_reviews": protection["required_pull_request_reviews"].get("dismiss_stale_reviews", False),
                "require_code_owner_reviews": protection["required_pull_request_reviews"].get("require_code_owner_reviews", False),
                "required_approving_review_count": protection["required_pull_request_reviews"].get("required_approving_review_count", 1),
                "bypass_pull_request_allowances": {
                    "users": bypass_users,
                    "teams": protection["required_pull_request_reviews"].get(
                        "bypass_pull_request_allowances", {}).get("teams", []),
                    "apps": protection["required_pull_request_reviews"].get(
                        "bypass_pull_request_allowances", {}).get("apps", [])
                }
            },
            "enforce_admins": original_setting  # Restore original setting
        }
        
        # Update protection
        url = f"{GITHUB_API_URL}/repos/{REPO}/branches/{branch}/protection"
        response = requests.put(url, headers=HEADERS, json=restored_protection)
        response.raise_for_status()
        print("Successfully restored branch protection rules")

if __name__ == "__main__":
    if len(sys.argv) < 3:
        print("Usage: python branch_protection_bypass.py <ACTION> <USER_ID_OR_SETTING>")
        sys.exit(1)
    
    modify_protection(sys.argv[1], sys.argv[2])
