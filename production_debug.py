#!/usr/bin/env python3
"""
Production debugging script for SIL PowerPoint Generator
Run this to diagnose issues in production
"""

import requests
import json
import time
from datetime import datetime

# Configuration - update this for your production URL
PRODUCTION_URL = "https://sil-ppt-v2.onrender.com/"  # Update this!
API_BASE = f"{PRODUCTION_URL}/api"


def test_basic_connectivity():
    """Test basic API connectivity"""
    print("\n=== Testing Basic Connectivity ===")

    endpoints = [
        "/health",
        "/teams",
        "/test-connection"
    ]

    for endpoint in endpoints:
        try:
            url = f"{API_BASE}{endpoint}"
            print(f"\nTesting {url}...")
            response = requests.get(url, timeout=10)
            print(f"Status: {response.status_code}")
            if response.ok:
                print(f"Response: {json.dumps(response.json(), indent=2)}")
            else:
                print(f"Error: {response.text}")
        except Exception as e:
            print(f"Failed: {str(e)}")


def test_job_creation_and_polling():
    """Test job creation and polling mechanism"""
    print("\n\n=== Testing Job Creation and Polling ===")

    # First, get a valid team
    try:
        teams_response = requests.get(f"{API_BASE}/teams")
        if not teams_response.ok:
            print("Failed to get teams")
            return

        teams = teams_response.json()['teams']
        if not teams:
            print("No teams available")
            return

        test_team = teams[0]
        print(f"Using team: {test_team['name']} ({test_team['key']})")

    except Exception as e:
        print(f"Failed to get teams: {str(e)}")
        return

    # Create a job
    print("\nCreating job...")
    try:
        create_response = requests.post(
            f"{API_BASE}/generate",
            json={"team_key": test_team['key']},
            timeout=10
        )

        print(f"Create status: {create_response.status_code}")
        if not create_response.ok:
            print(f"Create error: {create_response.text}")
            return

        job_data = create_response.json()
        job_id = job_data.get('job_id')
        print(f"Job created: {job_id}")
        print(f"Full response: {json.dumps(job_data, indent=2)}")

    except Exception as e:
        print(f"Failed to create job: {str(e)}")
        return

    # Test different polling endpoints
    print("\n\nTesting polling endpoints...")

    poll_endpoints = [
        f"/jobs/{job_id}",
        f"/jobs/{job_id}/",  # With trailing slash
        f"/jobs/{job_id}/status",
    ]

    for endpoint in poll_endpoints:
        try:
            url = f"{API_BASE}{endpoint}"
            print(f"\nPolling {url}...")
            response = requests.get(url, timeout=10)
            print(f"Status: {response.status_code}")

            if response.ok:
                print(f"Response: {json.dumps(response.json(), indent=2)}")
            else:
                print(f"Error: {response.text}")
                print(f"Headers: {dict(response.headers)}")

        except Exception as e:
            print(f"Failed: {str(e)}")

    # Try continuous polling
    print("\n\nTesting continuous polling...")
    max_polls = 10
    poll_count = 0

    while poll_count < max_polls:
        try:
            poll_url = f"{API_BASE}/jobs/{job_id}"
            print(f"\nPoll {poll_count + 1}: {poll_url}")

            response = requests.get(poll_url, timeout=10)

            if response.ok:
                job_status = response.json()
                status = job_status.get('status', 'unknown')
                progress = job_status.get('progress', 0)
                message = job_status.get('message', '')

                print(f"Status: {status} | Progress: {progress}% | Message: {message}")

                if status in ['completed', 'failed']:
                    print(f"\nJob finished with status: {status}")
                    if status == 'failed':
                        print(f"Error: {job_status.get('error', 'Unknown error')}")
                    break

            else:
                print(f"Poll failed: {response.status_code} - {response.text}")

        except Exception as e:
            print(f"Poll error: {str(e)}")

        poll_count += 1
        time.sleep(2)

    if poll_count >= max_polls:
        print("\nReached maximum poll count")


def test_download_behaviors():
    """Test the behaviors slide download"""
    print("\n\n=== Testing Behaviors Slide Download ===")

    try:
        # Get teams
        teams_response = requests.get(f"{API_BASE}/teams")
        if not teams_response.ok:
            print("Failed to get teams")
            return

        teams = teams_response.json()['teams']
        test_team = teams[0]

        # Test download
        download_url = f"{API_BASE}/download-behaviors-slide/{test_team['key']}"
        print(f"Testing download from: {download_url}")

        response = requests.get(download_url, timeout=30)
        print(f"Status: {response.status_code}")

        if response.ok:
            print(f"Download successful! Size: {len(response.content)} bytes")
            print(f"Content-Type: {response.headers.get('Content-Type')}")
        else:
            print(f"Download failed: {response.text}")

    except Exception as e:
        print(f"Download test failed: {str(e)}")


def diagnose_nginx_config():
    """Provide nginx configuration recommendations"""
    print("\n\n=== Nginx Configuration Recommendations ===")
    print("""
If you're using nginx as a reverse proxy, ensure these settings:

1. For SSE (Server-Sent Events) support:
   proxy_buffering off;
   proxy_cache off;
   proxy_set_header Connection '';
   proxy_http_version 1.1;
   chunked_transfer_encoding on;

2. For API routes:
   location /api/ {
       proxy_pass http://localhost:5001;
       proxy_set_header Host $host;
       proxy_set_header X-Real-IP $remote_addr;
       proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
       proxy_set_header X-Forwarded-Proto $scheme;

       # Timeout settings
       proxy_connect_timeout 300s;
       proxy_send_timeout 300s;
       proxy_read_timeout 300s;
   }

3. For debugging, check nginx logs:
   tail -f /var/log/nginx/error.log
   tail -f /var/log/nginx/access.log
""")


def main():
    """Run all diagnostic tests"""
    print(f"SIL PowerPoint Generator - Production Diagnostics")
    print(f"Testing URL: {PRODUCTION_URL}")
    print(f"Started at: {datetime.now()}")

    test_basic_connectivity()
    test_job_creation_and_polling()
    test_download_behaviors()
    diagnose_nginx_config()

    print(f"\n\nDiagnostics completed at: {datetime.now()}")


if __name__ == "__main__":
    main()