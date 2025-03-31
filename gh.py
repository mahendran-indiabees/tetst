import csv
import requests

# Configuration
TARGET_ORG = "your-target-org"
TARGET_REPO = "your-repo"
BACKUP_CSV = "your_backup_file.csv"
GITHUB_TOKEN = "your-personal-access-token"

headers = {
    "Authorization": f"token {GITHUB_TOKEN}",
    "Accept": "application/vnd.github.v3+json"
}

def get_target_teams():
    """Get all teams in target org with their members"""
    teams = {}
    url = f"https://api.github.com/orgs/{TARGET_ORG}/teams"
    response = requests.get(url, headers=headers)
    
    for team in response.json():
        members_url = team['members_url'].replace('{/member}', '')
        members_response = requests.get(members_url, headers=headers)
        members = [member['login'] for member in members_response.json()]
        teams[team['name']] = {
            'members': members,
            'permission': team['permission'] if 'permission' in team else None
        }
    return teams

def check_user_in_teams(username, target_teams):
    """Check which team a user belongs to in target org"""
    for team_name, team_data in target_teams.items():
        if username in team_data['members']:
            return team_name
    return "UserNotFound"

def compare_permissions():
    target_teams = get_target_teams()
    comparison_results = []
    
    with open(BACKUP_CSV, 'r') as csvfile:
        reader = csv.DictReader(csvfile)
        for row in reader:
            if row['UserType'] == 'DirectUser':
                # Handle direct users
                target_team = check_user_in_teams(row['Name'], target_teams)
                if target_team != "UserNotFound":
                    # Get the team's permission in target repo
                    team_permission = target_teams[target_team]['permission']
                    comparison_results.append({
                        'sno': len(comparison_results) + 1,
                        'UserType Source': 'DirectUser',
                        'user': row['Name'],
                        'source repo access': row['Access'],
                        'User Type in Target': target_team,
                        'target repo access': team_permission
                    })
                else:
                    comparison_results.append({
                        'sno': len(comparison_results) + 1,
                        'UserType Source': 'DirectUser',
                        'user': row['Name'],
                        'source repo access': row['Access'],
                        'User Type in Target': 'UserNotFound',
                        'target repo access': 'NA'
                    })
            elif row['UserType'] == 'Team':
                # Handle team members
                members = row['Members'].split(',') if row['Members'] else []
                for member in members:
                    target_team = check_user_in_teams(member, target_teams)
                    if target_team != "UserNotFound":
                        team_permission = target_teams[target_team]['permission']
                        comparison_results.append({
                            'sno': len(comparison_results) + 1,
                            'UserType Source': row['Name'],
                            'user': member,
                            'source repo access': row['Access'],
                            'User Type in Target': target_team,
                            'target repo access': team_permission
                        })
                    else:
                        comparison_results.append({
                            'sno': len(comparison_results) + 1,
                            'UserType Source': row['Name'],
                            'user': member,
                            'source repo access': row['Access'],
                            'User Type in Target': 'UserNotFound',
                            'target repo access': 'NA'
                        })
    
    # Save comparison results
    with open('permission_comparison.csv', 'w', newline='') as outfile:
        fieldnames = ['sno', 'UserType Source', 'user', 'source repo access', 
                     'User Type in Target', 'target repo access']
        writer = csv.DictWriter(outfile, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(comparison_results)
    
    print("Permission comparison saved to permission_comparison.csv")

if __name__ == "__main__":
    compare_permissions()
