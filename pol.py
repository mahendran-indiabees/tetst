import requests
import json
import base64
import argparse
from datetime import datetime

# Azure DevOps Policy Type Constants with complete settings mapping
POLICY_TYPES = {
    "fa4e907d-c16b-4a4c-9dfa-4906e5d171dd": {
        "name": "Minimum number of reviewers",
        "settings": {
            "minimumApproverCount": "Minimum approvers",
            "creatorVoteCounts": "Creator vote counts (inverted)",
            "allowDownvotes": "Allow downvotes",
            "resetOnSourcePush": "Reset votes on new changes",
            "requiredVoteOnLastIteration": "Require vote on last iteration",
            "resetRejectionsOnSourcePush": "Reset rejections on new changes",
            "blockLastPusherVote": "Block last pusher's vote"
        }
    },
    "fd2167ab-b0be-447a-8ec8-39368250530e": {
        "name": "Merge strategy",
        "settings": {
            "allowNoFastForward": "Basic merge (no fast-forward)",
            "allowSquash": "Squash merge",
            "allowRebase": "Rebase + fast-forward",
            "allowRebaseMerge": "Rebase + merge commit",
            "allowConflictResolution": "Allow conflict resolution"
        }
    },
    "40e92b44-2fe1-4dd6-b3d8-74a9c21d0c6e": {
        "name": "Work item linking",
        "settings": {
            "required": "Require linked work items",
            "validateLinkedWorkItems": "Validate work item state",
            "scopes[0].validateLinkedArtifacts": "Validate across artifact links"
        }
    },
    "c6a1889d-b943-4856-b76f-9e46bb6b0df2": {
        "name": "Comment requirements",
        "settings": {
            "required": "Require comments resolution"
        }
    },
    "2e26e725-8201-4edd-8bf5-978563c34a80": {
        "name": "Build validation",
        "settings": {
            "buildDefinitionId": "Build definition ID",
            "queueOnSourceUpdateOnly": "Trigger on source changes only",
            "validDuration": "Timeout (minutes)",
            "pathFilters": "Path filters",
            "manualQueueOnly": "Manual queue only",
            "displayName": "Display name"
        }
    },
    "0609b952-1397-4640-95ec-e00a01b2c241": {
        "name": "Status check",
        "settings": {
            "statusGenre": "Status genre",
            "statusName": "Status name",
            "validDuration": "Timeout (minutes)",
            "authorId": "Author ID"
        }
    },
    "0e0e67a5-cea6-4a0a-a5cd-0a934151e595": {
        "name": "Automatic reviewers",
        "settings": {
            "requiredReviewerIds": "Required reviewer IDs",
            "message": "Reviewer message",
            "pathFilters": "Path filters"
        }
    }
}

def pat_to_base64(pat):
    """Convert PAT to Base64 auth token"""
    return base64.b64encode(f":{pat}".encode()).decode()

def get_policies(org_url, pat, project, params=None):
    """Retrieve policies with pagination handling"""
    policies = []
    continuation_token = None
    
    while True:
        url = f"{org_url}/{project}/_apis/policy/configurations?api-version=6.0"
        headers = {"Authorization": f"Basic {pat_to_base64(pat)}"}
        
        query_params = params.copy() if params else {}
        if continuation_token:
            query_params['continuationToken'] = continuation_token
        
        response = requests.get(url, headers=headers, params=query_params)
        response.raise_for_status()
        
        data = response.json()
        policies.extend(data["value"])
        
        continuation_token = response.headers.get("X-MS-ContinuationToken")
        if not continuation_token:
            break
    
    return policies

def get_repo_id(org_url, pat, project, repo):
    """Get repository GUID"""
    url = f"{org_url}/{project}/_apis/git/repositories/{repo}?api-version=6.0"
    response = requests.get(
        url,
        headers={"Authorization": f"Basic {pat_to_base64(pat)}"}
    )
    response.raise_for_status()
    return response.json()["id"]

def save_to_json(data, filename):
    """Save data to JSON file"""
    with open(filename, 'w') as f:
        json.dump(data, f, indent=2)
    return filename

def filter_repo_policies(repo_policies, project_policy_ids):
    """Filter out project-level policies from repo policies"""
    return [p for p in repo_policies if p['id'] not in project_policy_ids]

def get_nested_setting(settings, key):
    """Access nested settings using dot notation"""
    keys = key.split('.')
    value = settings
    for k in keys:
        if isinstance(value, list) and len(value) > 0:
            value = value[0].get(k, None)
        else:
            value = value.get(k, None)
        if value is None:
            return None
    return value

def format_policy(policy, policy_level):
    """Convert policy to human-readable format with all settings"""
    lines = []
    policy_type_id = policy['type']['id']
    settings = policy.get('settings', {})
    scope = settings.get('scope', [{}])[0]
    policy_info = POLICY_TYPES.get(policy_type_id, {"name": policy_type_id, "settings": {}})

    # Policy Header
    lines.append(f"\n{policy_level}. Configuration: {policy_level} Level")
    lines.append("=" * 40)
    lines.append(f"Policy ID: {policy['id']}")
    lines.append(f"Branch: {scope.get('refName', 'All branches')}")
    lines.append(f"Match type: {scope.get('matchKind', 'exact')}")
    
    # Policy Type
    lines.append(f"\nTYPE: {policy_info['name']}")
    
    # Settings
    lines.append("[SETTINGS]")
    
    # Format all known settings for this policy type
    for setting_key, display_name in policy_info['settings'].items():
        value = get_nested_setting(settings, setting_key)
        
        # Special handling for inverted boolean
        if setting_key == "creatorVoteCounts":
            value = not bool(value)
        
        # Special handling for duration (seconds to minutes)
        if setting_key == "validDuration" and value is not None:
            value = int(value) // 60
        
        if value is not None:
            if isinstance(value, list):
                lines.append(f"• {display_name}:")
                for item in value:
                    lines.append(f"  - {item}")
            else:
                lines.append(f"• {display_name}: {value}")
    
    return "\n".join(lines)

def generate_human_readable_report(project_policies, repo_policies):
    """Generate human-readable report"""
    report = []
    
    # Add project level policies
    for i, policy in enumerate(project_policies, 1):
        report.append(format_policy(policy, f"{i}"))
    
    # Add repository level policies
    offset = len(project_policies) + 1
    for i, policy in enumerate(repo_policies, offset):
        report.append(format_policy(policy, f"{i}"))
    
    return "\n".join(report)

def main():
    parser = argparse.ArgumentParser(description="Backup ADO branch policies for migration")
    parser.add_argument("--org-url", required=True, help="ADO organization URL")
    parser.add_argument("--pat", required=True, help="Personal Access Token")
    parser.add_argument("--project", required=True, help="Project name")
    parser.add_argument("--repo", required=True, help="Repository name")
    args = parser.parse_args()

    try:
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        
        # Step 1: Get project level policies
        print("Getting project level policies...")
        project_policies = get_policies(args.org_url, args.pat, args.project)
        project_policy_ids = {p['id'] for p in project_policies}
        save_to_json(project_policies, f"project_policies_{timestamp}.json")
        
        # Step 2: Get repository ID
        print("Getting repository ID...")
        repo_id = get_repo_id(args.org_url, args.pat, args.project, args.repo)
        
        # Step 3: Get repository level policies
        print("Getting repository level policies...")
        repo_policies = get_policies(args.org_url, args.pat, args.project, {'repositoryId': repo_id})
        save_to_json(repo_policies, f"repo_policies_{timestamp}.json")
        
        # Step 4: Filter out project policies from repo policies
        filtered_repo_policies = filter_repo_policies(repo_policies, project_policy_ids)
        
        # Step 5: Generate human-readable report
        print("Generating report...")
        report = generate_human_readable_report(project_policies, filtered_repo_policies)
        
        # Save report
        report_filename = f"policy_report_{timestamp}.txt"
        with open(report_filename, 'w') as f:
            f.write(report)
        
        print(f"\nSuccessfully generated report: {report_filename}")
        print(f"Project policies found: {len(project_policies)}")
        print(f"Repository-specific policies found: {len(filtered_repo_policies)}")
    
    except Exception as e:
        print(f"Error: {str(e)}")
        exit(1)

if __name__ == "__main__":
    main()
