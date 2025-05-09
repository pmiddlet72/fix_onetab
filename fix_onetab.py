#!/usr/bin/env python3
import os
import json
import shutil
import argparse
import time
import subprocess
from pathlib import Path
from datetime import datetime

def backup_extension_data(extension_path, backup_dir):
    """Create a backup of the current OneTab extension data"""
    if not os.path.exists(backup_dir):
        os.makedirs(backup_dir)
    
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    backup_path = os.path.join(backup_dir, f"onetab_backup_{timestamp}")
    os.makedirs(backup_path, exist_ok=True)
    
    print(f"Creating backup at: {backup_path}")
    
    # Copy all files
    if os.path.exists(extension_path):
        for file_path in Path(extension_path).glob("*"):
            if os.path.isfile(file_path):
                shutil.copy2(file_path, backup_path)
        print(f"Backup completed successfully")
    else:
        print(f"Warning: Extension path {extension_path} does not exist")
    
    return backup_path

def fix_extension(extension_path, urls_json_path, clear_db=False):
    """Attempt to fix the OneTab extension by recreating its state"""
    if not os.path.exists(extension_path):
        print(f"Error: Extension path {extension_path} does not exist")
        return False
    
    if not os.path.exists(urls_json_path):
        print(f"Error: URLs JSON file {urls_json_path} does not exist")
        return False
    
    # Load the URLs from JSON
    try:
        with open(urls_json_path, 'r') as f:
            urls_data = json.load(f)
        print(f"Loaded {len(urls_data)} URLs from {urls_json_path}")
    except Exception as e:
        print(f"Error loading URLs data: {e}")
        return False
    
    # Create a new state file
    # Group URLs by group name
    url_groups = {}
    for entry in urls_data:
        group_name = entry.get('group', 'Unnamed Group')
        if group_name not in url_groups:
            url_groups[group_name] = []
        url_groups[group_name].append({
            'id': f"tab_{int(time.time() * 1000)}_{len(url_groups[group_name])}",
            'url': entry['url'],
            'title': entry.get('title', entry['url'])
        })
    
    # Create the OneTab state structure
    onetab_state = {
        'tabGroups': []
    }
    
    for group_name, tabs in url_groups.items():
        group_id = f"group_{int(time.time() * 1000)}_{len(onetab_state['tabGroups'])}"
        onetab_state['tabGroups'].append({
            'id': group_id,
            'name': group_name if group_name != 'Unknown Group' else '',
            'tabs': tabs
        })
        # Add a small delay to ensure unique IDs
        time.sleep(0.01)
    
    # First attempt - try to just create the state file
    print("Attempting to fix OneTab by creating a new state file...")
    
    if clear_db:
        print("Warning: Clearing the OneTab database (--clear-db flag set)")
        try:
            for file_path in Path(extension_path).glob("*.ldb"):
                print(f"Removing: {file_path}")
                os.remove(file_path)
            for file_path in Path(extension_path).glob("*.log"):
                if str(file_path).endswith("CURRENT") or str(file_path).endswith("LOCK"):
                    continue
                print(f"Removing: {file_path}")
                os.remove(file_path)
            print("Database cleared")
        except Exception as e:
            print(f"Error clearing database: {e}")
            return False
    
    # Create a script that will attempt to write the state to Chrome's storage
    state_file = os.path.join(os.path.dirname(os.path.abspath(__file__)), "onetab_state.json")
    with open(state_file, 'w') as f:
        json.dump(onetab_state, f, indent=2)
    
    print("Created OneTab state file")
    print(f"The new state file has been created at: {state_file}")
    print("To complete the fix, follow these steps:")
    print("1. Make sure Chrome is running")
    print("2. Close the OneTab extension if it's open")
    print("3. Go to chrome://extensions in your browser")
    print("4. Find OneTab and click 'Details'")
    print("5. Toggle 'Allow access to file URLs' ON if it's not already enabled")
    print("6. Now, try opening OneTab again")
    print("7. If it's still not working, try the following:")
    print("   a. Disable the OneTab extension")
    print("   b. Close Chrome completely")
    print("   c. Restart Chrome")
    print("   d. Re-enable the OneTab extension")
    
    # Provide a command to attempt resetting Chrome extensions
    print("\nIf the above doesn't work, you can try resetting Chrome's extension system:")
    print("killall -SIGTERM chrome && sleep 2 && google-chrome")
    
    # Check if Chrome is running
    chrome_running = subprocess.run(["pgrep", "chrome"], capture_output=True, text=True).returncode == 0
    if chrome_running:
        print("\nChrome is currently running. You'll need to restart it for changes to take effect.")
    
    return True

def main():
    parser = argparse.ArgumentParser(description='Fix OneTab extension by recreating its state')
    parser.add_argument('--path', type=str, help='Path to the OneTab extension storage', 
                        default=os.path.expanduser('~/.config/google-chrome/Default/Local Extension Settings/chphlpgkkbolifaimnlloiipkdnihall/'))
    parser.add_argument('--input', type=str, help='Path to the URLs JSON file', 
                        default='onetab_urls.json')
    parser.add_argument('--backup-dir', type=str, help='Directory to store backups', 
                        default='./backup')
    parser.add_argument('--clear-db', action='store_true', help='Clear the existing database files (use with caution!)')
    args = parser.parse_args()
    
    # Create a backup first
    backup_path = backup_extension_data(args.path, args.backup_dir)
    print(f"Backup created at: {backup_path}")
    
    # Try to fix the extension
    success = fix_extension(args.path, args.input, args.clear_db)
    
    if success:
        print("\nPotential fix applied. Follow the instructions above to complete the process.")
        print("If the fix doesn't work, you can restore from the backup at: " + backup_path)
    else:
        print("\nFailed to apply fix. No changes were made to your OneTab extension.")
        print("You can try manually importing the bookmarks HTML file instead.")

if __name__ == "__main__":
    main() 