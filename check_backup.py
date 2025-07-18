#!/usr/bin/env python3
"""
check_backup_folder.py
Quick script to check backup folder creation and permissions
"""

from pathlib import Path
import os
import shutil
from datetime import datetime


def check_and_create_backup():
    """Check if backup folder exists and create if needed"""

    # Find the fans directory
    current_path = Path.cwd()
    print(f"Current working directory: {current_path}")

    # Try to find assets/logos/fans
    fans_dir = None

    # Method 1: Direct path from current location
    if (current_path / 'assets' / 'logos' / 'fans').exists():
        fans_dir = current_path / 'assets' / 'logos' / 'fans'
    # Method 2: Search upward
    else:
        temp_path = current_path
        while temp_path.parent != temp_path:
            if (temp_path / 'assets' / 'logos' / 'fans').exists():
                fans_dir = temp_path / 'assets' / 'logos' / 'fans'
                break
            temp_path = temp_path.parent

    if not fans_dir:
        print("❌ Could not find assets/logos/fans directory!")
        print("Make sure you're running this from the project root")
        return

    print(f"✅ Found fans directory: {fans_dir}")

    # Check if backups folder exists
    backup_dir = fans_dir / 'backups'

    if backup_dir.exists():
        print(f"✅ Backup directory already exists: {backup_dir}")
    else:
        print(f"❌ Backup directory not found")

        # Try to create it
        try:
            backup_dir.mkdir(exist_ok=True)
            print(f"✅ Created backup directory: {backup_dir}")
        except PermissionError:
            print(f"❌ Permission denied! Cannot create backup directory")
            print(f"   Try running with sudo or check folder permissions")
            return
        except Exception as e:
            print(f"❌ Error creating backup directory: {str(e)}")
            return

    # List current fan images
    print(f"\n📁 Current fan images:")
    image_files = list(fans_dir.glob("*_Fanpic.*"))

    if not image_files:
        print("   No fan images found")
    else:
        for img in sorted(image_files):
            print(f"   - {img.name} ({img.stat().st_size:,} bytes)")

    # Check if we can write to backup directory
    test_file = backup_dir / 'test_write.txt'
    try:
        test_file.write_text('test')
        test_file.unlink()  # Remove test file
        print(f"\n✅ Backup directory is writable")
    except:
        print(f"\n❌ Cannot write to backup directory - check permissions")

    # Create manual backups of existing images
    print(f"\n💾 Creating manual backups...")
    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')

    for img_path in image_files:
        backup_path = backup_dir / f"{img_path.stem}_manual_backup_{timestamp}{img_path.suffix}"
        try:
            shutil.copy2(img_path, backup_path)
            print(f"   ✅ Backed up: {img_path.name} -> {backup_path.name}")
        except Exception as e:
            print(f"   ❌ Failed to backup {img_path.name}: {str(e)}")

    # Show final structure
    print(f"\n📁 Final structure:")
    print(f"   {fans_dir}/")
    for item in sorted(fans_dir.iterdir()):
        if item.is_dir():
            print(f"   ├── {item.name}/")
            for subitem in sorted(item.iterdir())[:5]:  # Show first 5 files
                print(f"   │   └── {subitem.name}")
            if len(list(item.iterdir())) > 5:
                print(f"   │   └── ... and {len(list(item.iterdir())) - 5} more files")
        else:
            print(f"   ├── {item.name}")


if __name__ == "__main__":
    check_and_create_backup()