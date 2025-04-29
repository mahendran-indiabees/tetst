import csv
import requests
from requests.auth import HTTPBasicAuth
from datetime import datetime

# Configuration
BITBUCKET_URL = "https://your-bitbucket-server.example.com"
USERNAME = "your_username"
PASSWORD = "your_password_or_personal_access_token"  # Recommended
INPUT_CSV = "repos_list.csv"  # Your input CSV file
OUTPUT_CSV = "repos_with_dates.csv"  # Output file with creation dates

def get_repo_creation_date(project_key, repo_slug):
    """
    Get creation date for a specific repository
    Returns timestamp in milliseconds and readable date string
    """
    api_url = f"{BITBUCKET_URL}/rest/api/1.0/projects/{project_key}/repos/{repo_slug}"
    
    try:
        response = requests.get(
            api_url,
            auth=HTTPBasicAuth(USERNAME, PASSWORD),
            timeout=10
        )
        
        if response.status_code == 200:
            repo_data = response.json()
            created_date = repo_data.get('createdDate')
            if created_date:
                readable_date = datetime.fromtimestamp(created_date / 1000).strftime('%Y-%m-%d %H:%M:%S')
                return created_date, readable_date
            return None, "Date not available"
        elif response.status_code == 404:
            return None, "Repository not found"
        else:
            return None, f"API Error: {response.status_code}"
    
    except Exception as e:
        return None, f"Request failed: {str(e)}"

def process_repos_csv(input_file, output_file):
    """
    Process the input CSV and create output with creation dates
    """
    with open(input_file, mode='r', encoding='utf-8') as infile, \
         open(output_file, mode='w', newline='', encoding='utf-8') as outfile:
        
        reader = csv.DictReader(infile)
        fieldnames = reader.fieldnames + ['created_timestamp', 'created_date', 'status']
        writer = csv.DictWriter(outfile, fieldnames=fieldnames)
        writer.writeheader()
        
        for row in reader:
            project = row['project_name'].strip()
            repo = row['repo_name'].strip()
            
            print(f"Processing {project}/{repo}...")
            timestamp, date = get_repo_creation_date(project, repo)
            
            output_row = {
                **row,
                'created_timestamp': timestamp,
                'created_date': date,
                'status': "Success" if timestamp else "Failed"
            }
            writer.writerow(output_row)
            
            print(f"  -> Created: {date}")

if __name__ == "__main__":
    print(f"Reading repositories from {INPUT_CSV}...")
    print(f"Will write results to {OUTPUT_CSV}")
    
    process_repos_csv(INPUT_CSV, OUTPUT_CSV)
    
    print("\nProcessing complete!")
