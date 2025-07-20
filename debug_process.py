#!/usr/bin/env python3
"""
Simple progress monitor - just watch the progress updates
No complex imports, just HTTP requests
"""

import requests
import time
import sys
from datetime import datetime

API_BASE = "http://localhost:5001/api"


def monitor_progress():
    """Monitor PowerPoint generation progress"""
    print("PowerPoint Generation Progress Monitor")
    print("=" * 60)

    # 1. Check server
    try:
        r = requests.get(f"{API_BASE}/health")
        if r.status_code == 200:
            print("✅ Server is running")
        else:
            print("❌ Server error:", r.status_code)
            return
    except Exception as e:
        print("❌ Cannot connect to server:", e)
        print("\nMake sure the Flask server is running:")
        print("  cd backend")
        print("  python app.py")
        return

    # 2. Get team or use default
    team_key = sys.argv[1] if len(sys.argv) > 1 else "utah_jazz"
    print(f"\nUsing team: {team_key}")

    # 3. Start generation
    print("\nStarting PowerPoint generation...")
    try:
        r = requests.post(
            f"{API_BASE}/generate",
            json={"team_key": team_key}
        )
        if r.status_code != 200:
            print("❌ Failed to start:", r.text)
            return

        data = r.json()
        job_id = data['job_id']
        print(f"✅ Job started: {job_id}")

    except Exception as e:
        print("❌ Error starting job:", e)
        return

    # 4. Monitor progress
    print("\nMonitoring progress...")
    print("-" * 60)

    progress_points = []
    start_time = time.time()
    last_progress = -1

    while True:
        try:
            # Get status
            r = requests.get(f"{API_BASE}/jobs/{job_id}/status")
            if r.status_code != 200:
                print(f"❌ Status error: {r.status_code}")
                break

            data = r.json()
            progress = data.get('progress', 0)
            status = data.get('status', 'unknown')
            message = data.get('message', '')

            # Print if progress changed
            if progress != last_progress:
                elapsed = time.time() - start_time
                timestamp = datetime.now().strftime("%H:%M:%S")
                print(f"[{timestamp}] [{elapsed:6.1f}s] {progress:3d}% - {message}")
                progress_points.append(progress)
                last_progress = progress

            # Check completion
            if status == 'completed':
                print("-" * 60)
                print(f"\n✅ COMPLETED in {elapsed:.1f} seconds!")
                break
            elif status == 'failed':
                print("-" * 60)
                print(f"\n❌ FAILED: {data.get('error', 'Unknown error')}")
                break

            # Timeout check
            if elapsed > 300:  # 5 minutes
                print("\n❌ Timeout after 5 minutes")
                break

        except Exception as e:
            print(f"\n❌ Error monitoring: {e}")
            break

        time.sleep(0.5)  # Poll every 500ms

    # Summary
    print("\nSummary:")
    print(f"  Total progress points: {len(progress_points)}")
    print(f"  Progress sequence: {progress_points}")
    print(f"  Expected ~25-30 updates, got {len(progress_points)}")

    if len(progress_points) < 10:
        print("\n⚠️  Too few progress updates!")
        print("The issue is likely that PowerPointBuilder progress updates aren't reaching the backend.")
        print("\nTo debug further:")
        print("1. Check Flask server console for any errors")
        print("2. Add debug logging to PowerPointBuilder.__init__ to verify job_id is received")
        print("3. Add debug logging to update_progress() in pptx_builder.py")


if __name__ == "__main__":
    monitor_progress()