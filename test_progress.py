#!/usr/bin/env python3
"""
Test script to validate progress tracking is working correctly
Run this from the project root directory
"""

import sys
import os
from pathlib import Path
import time
from datetime import datetime

# Add project root to path
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

# Set up environment
os.environ['SNOWFLAKE_ACCOUNT'] = os.getenv('SNOWFLAKE_ACCOUNT', 'test')
os.environ['SNOWFLAKE_USER'] = os.getenv('SNOWFLAKE_USER', 'test')
os.environ['SNOWFLAKE_PASSWORD'] = os.getenv('SNOWFLAKE_PASSWORD', 'test')

# Import what we need
from report_builder.pptx_builder import PowerPointBuilder

# Track all progress updates
progress_updates = []


def test_progress_callback(progress: int, message: str):
    """Test callback that records all progress updates"""
    timestamp = datetime.now().strftime('%H:%M:%S.%f')[:-3]
    progress_updates.append({
        'time': timestamp,
        'progress': progress,
        'message': message
    })
    print(f"[{timestamp}] {progress:3d}% - {message}")


def test_progress_tracking():
    """Test the progress tracking implementation"""
    print("\n" + "=" * 60)
    print("PROGRESS TRACKING TEST")
    print("=" * 60 + "\n")

    # Test 1: Basic callback functionality
    print("Test 1: Testing callback is properly connected...")
    try:
        # Create a simple test builder
        builder = PowerPointBuilder(
            team_key='utah_jazz',
            job_id='test-job-123',
            progress_callback=test_progress_callback
        )

        # Check if callback is stored
        if hasattr(builder, 'progress_callback') and builder.progress_callback is not None:
            print("✅ Progress callback successfully stored in PowerPointBuilder")
        else:
            print("❌ Progress callback NOT stored properly")
            return False

    except Exception as e:
        print(f"❌ Error creating PowerPointBuilder: {e}")
        return False

    print("\nTest 2: Testing progress updates...")

    # Clear progress updates
    progress_updates.clear()

    # Import and call update_progress directly
    from report_builder.pptx_builder import update_progress

    # Simulate some progress updates
    test_updates = [
        (5, "Starting test..."),
        (25, "Processing data..."),
        (50, "Halfway there..."),
        (75, "Almost done..."),
        (100, "Test complete!")
    ]

    for progress, message in test_updates:
        update_progress(progress, message)
        time.sleep(0.1)  # Small delay to see updates

    print(f"\nReceived {len(progress_updates)} progress updates")

    if len(progress_updates) == len(test_updates):
        print("✅ All progress updates were captured by callback")
    else:
        print(f"❌ Expected {len(test_updates)} updates but got {len(progress_updates)}")
        return False

    # Test 3: Check update contents
    print("\nTest 3: Verifying update contents...")
    all_correct = True
    for i, (expected, actual) in enumerate(zip(test_updates, progress_updates)):
        if expected[0] == actual['progress'] and expected[1] == actual['message']:
            print(f"✅ Update {i + 1}: {actual['progress']}% - {actual['message']}")
        else:
            print(f"❌ Update {i + 1} mismatch:")
            print(f"   Expected: {expected[0]}% - {expected[1]}")
            print(f"   Actual: {actual['progress']}% - {actual['message']}")
            all_correct = False

    if not all_correct:
        return False

    # Test 4: Test without callback (should still work, just log)
    print("\nTest 4: Testing without callback (should just log)...")
    builder_no_callback = PowerPointBuilder(
        team_key='utah_jazz',
        job_id='test-job-456'
        # No callback provided
    )

    # This should work without error
    try:
        update_progress(50, "Testing without callback")
        print("✅ Progress update works without callback")
    except Exception as e:
        print(f"❌ Error updating progress without callback: {e}")
        return False

    print("\n" + "=" * 60)
    print("ALL TESTS PASSED! ✅")
    print("=" * 60)
    print("\nProgress tracking is working correctly!")
    print(f"Total progress updates captured: {len(progress_updates)}")

    return True


def test_full_integration():
    """Test with actual presentation build (requires database connection)"""
    print("\n" + "=" * 60)
    print("FULL INTEGRATION TEST (Optional)")
    print("=" * 60 + "\n")

    response = input("Run full integration test? This requires Snowflake connection (y/n): ")
    if response.lower() != 'y':
        print("Skipping integration test")
        return

    print("\nStarting full presentation build with progress tracking...")

    # Clear previous updates
    progress_updates.clear()

    try:
        # This simulates what app.py does
        def progress_callback(progress: int, message: str):
            """Integration test callback"""
            print(f"[INTEGRATION] {progress:3d}% - {message}")
            progress_updates.append((progress, message))

        builder = PowerPointBuilder(
            team_key='utah_jazz',
            job_id='integration-test',
            progress_callback=progress_callback
        )

        # Try to build (will fail if no database, but we can see progress)
        output_path = builder.build_presentation(
            include_custom_categories=False  # Faster for testing
        )

        print(f"\n✅ Presentation built successfully: {output_path}")

    except Exception as e:
        print(f"\n⚠️  Build failed (expected if no database): {e}")

    print(f"\nCaptured {len(progress_updates)} progress updates during build")
    if len(progress_updates) > 10:
        print("✅ Granular progress tracking is working!")
        print("\nFirst 5 updates:")
        for p, m in progress_updates[:5]:
            print(f"  {p:3d}% - {m}")
        print("\nLast 5 updates:")
        for p, m in progress_updates[-5:]:
            print(f"  {p:3d}% - {m}")
    else:
        print("❌ Expected more progress updates")


if __name__ == "__main__":
    # Run the basic test
    success = test_progress_tracking()

    if success:
        # Optionally run integration test
        test_full_integration()
    else:
        print("\n❌ Basic tests failed, skipping integration test")
        sys.exit(1)