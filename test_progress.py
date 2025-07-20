#!/usr/bin/env python3
"""
Test script to verify progress tracking works correctly
Run this from the project root directory
"""

import os
import sys
import time
import json
import threading
import requests
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

# Configuration
API_BASE = "http://localhost:5001/api"
DEFAULT_TEAM_KEY = "utah_jazz"  # Default team to test


def test_progress_tracking(team_key=None):
    """Test the progress tracking functionality"""
    if team_key is None:
        team_key = DEFAULT_TEAM_KEY

    print("=" * 60)
    print("TESTING PROGRESS TRACKING")
    print("=" * 60)

    # Step 1: Check if server is running
    print("\n1. Checking if server is running...")
    try:
        response = requests.get(f"{API_BASE}/health")
        if response.status_code == 200:
            print("✓ Server is running")
        else:
            print("✗ Server returned status:", response.status_code)
            print("Please start the Flask server with: python backend/app.py")
            return
    except requests.ConnectionError:
        print("✗ Cannot connect to server at", API_BASE)
        print("Please start the Flask server with: python backend/app.py")
        return

    # Step 2: Test database connection
    print("\n2. Testing database connection...")
    response = requests.get(f"{API_BASE}/test-connection")
    data = response.json()
    if data.get('connected'):
        print("✓ Database connection successful")
    else:
        print("✗ Database connection failed:", data.get('error', 'Unknown error'))
        return

    # Step 3: Get available teams
    print("\n3. Getting available teams...")
    response = requests.get(f"{API_BASE}/teams")
    teams_data = response.json()
    teams = teams_data.get('teams', [])

    if not teams:
        print("✗ No teams found")
        return

    print(f"✓ Found {len(teams)} teams")
    print("Available teams:")
    for team in teams[:5]:  # Show first 5 teams
        print(f"  - {team['name']} ({team['key']})")

    # Check if our test team exists
    team_exists = any(team['key'] == team_key for team in teams)
    if not team_exists:
        print(f"\n✗ Test team '{team_key}' not found")
        print("Using first available team instead...")
        team_key = teams[0]['key']
        team_name = teams[0]['name']
        print(f"Selected: {team_name} ({team_key})")
    else:
        team_name = next(team['name'] for team in teams if team['key'] == team_key)

    # Step 4: Start PowerPoint generation
    print(f"\n4. Starting PowerPoint generation for {team_name}...")
    response = requests.post(
        f"{API_BASE}/generate",
        json={
            "team_key": team_key,
            "skip_custom": False,  # Include custom categories
            "custom_count": 2  # Generate 2 custom categories
        }
    )

    if response.status_code != 200:
        print("✗ Failed to start generation:", response.text)
        return

    job_data = response.json()
    job_id = job_data.get('job_id')
    print(f"✓ Job started with ID: {job_id}")

    # Step 5: Monitor progress
    print("\n5. Monitoring progress...")
    print("-" * 50)

    last_progress = -1
    last_message = ""
    start_time = time.time()
    timeout = 300  # 5 minutes timeout

    while True:
        # Poll job status
        try:
            response = requests.get(f"{API_BASE}/jobs/{job_id}/status")
            if response.status_code != 200:
                print(f"\n✗ Failed to get job status: {response.status_code}")
                break

            status_data = response.json()
            status = status_data.get('status')
            progress = status_data.get('progress', 0)
            message = status_data.get('message', '')

            # Only print if progress changed
            if progress != last_progress or message != last_message:
                elapsed = time.time() - start_time
                print(f"[{elapsed:5.1f}s] {progress:3d}% - {message}")
                last_progress = progress
                last_message = message

            # Check if completed or failed
            if status == 'completed':
                print("-" * 50)
                elapsed = time.time() - start_time
                print(f"\n✓ Job completed successfully in {elapsed:.1f} seconds!")

                # Try to download the file
                print("\n6. Checking if file can be downloaded...")
                download_url = f"{API_BASE}/jobs/{job_id}/download"
                response = requests.head(download_url)
                if response.status_code == 200:
                    print(f"✓ File is ready for download at: {download_url}")
                else:
                    print(f"✗ File download returned status: {response.status_code}")
                break

            elif status == 'failed':
                print("-" * 50)
                error = status_data.get('error', 'Unknown error')
                print(f"\n✗ Job failed: {error}")
                break

        except requests.RequestException as e:
            print(f"\n✗ Request error: {e}")
            break

        # Wait before next poll
        time.sleep(1)

        # Timeout check
        if time.time() - start_time > timeout:
            print("\n✗ Timeout: Job took too long")
            break

    print("\n" + "=" * 60)
    print("TEST COMPLETE")
    print("=" * 60)


def test_progress_with_sse(team_key=None):
    """Test progress tracking using Server-Sent Events (SSE)"""
    if team_key is None:
        team_key = DEFAULT_TEAM_KEY

    print("\n" + "=" * 60)
    print("TESTING WITH SERVER-SENT EVENTS")
    print("=" * 60)

    # Start a job
    print(f"\nStarting PowerPoint generation for {team_key}...")
    response = requests.post(
        f"{API_BASE}/generate",
        json={"team_key": team_key}
    )

    if response.status_code != 200:
        print("✗ Failed to start generation")
        return

    job_id = response.json()['job_id']
    print(f"✓ Job started: {job_id}")
    print("\nMonitoring with SSE...")
    print("-" * 50)

    # Monitor with SSE
    try:
        start_time = time.time()
        last_progress = -1

        # Connect to SSE endpoint
        response = requests.get(
            f"{API_BASE}/jobs/{job_id}/progress",
            stream=True,
            headers={'Accept': 'text/event-stream'}
        )

        for line in response.iter_lines():
            if line:
                line_str = line.decode('utf-8')
                if line_str.startswith('data: '):
                    data_str = line_str[6:]  # Remove 'data: ' prefix
                    try:
                        data = json.loads(data_str)
                        progress = data.get('progress', 0)
                        message = data.get('message', '')
                        status = data.get('status')

                        if progress != last_progress:
                            elapsed = time.time() - start_time
                            print(f"[{elapsed:5.1f}s] {progress:3d}% - {message}")
                            last_progress = progress

                        if status in ['completed', 'failed']:
                            print("-" * 50)
                            if status == 'completed':
                                print(f"\n✓ Completed in {elapsed:.1f} seconds!")
                            else:
                                print(f"\n✗ Failed: {data.get('error', 'Unknown error')}")
                            break
                    except json.JSONDecodeError:
                        pass

    except Exception as e:
        print(f"\n✗ SSE Error: {e}")
        print("Note: SSE might not work in all environments. Polling is more reliable.")


def main():
    """Run all tests"""
    # Test 1: Basic progress tracking with polling
    test_progress_tracking()

    # Test 2: Optional SSE test (comment out if not needed)
    # print("\n\nWould you like to test Server-Sent Events (SSE)? (y/n): ", end='')
    # if input().lower() == 'y':
    #     test_progress_with_sse()


if __name__ == "__main__":
    # Check if we're in the right directory
    if not Path("backend/app.py").exists():
        print("Error: Please run this script from the project root directory")
        print("Usage: python test_progress.py")
        sys.exit(1)

    print("Sports Innovation Lab - Progress Tracking Test")
    print("=" * 60)
    print(f"API Base: {API_BASE}")
    print(f"Default Test Team: {DEFAULT_TEAM_KEY}")
    print("=" * 60)

    # You can also specify a team as command line argument
    if len(sys.argv) > 1:
        team_key = sys.argv[1]
        print(f"Using specified team: {team_key}")
        main_team = team_key
    else:
        main_team = None

    main()