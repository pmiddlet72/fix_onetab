#!/usr/bin/env python3
import os
import json
import re
import sys
import argparse
import subprocess
from pathlib import Path

def extract_onetab_data_from_files(leveldb_path, output_file=None):
    """
    Extract OneTab data from LevelDB files using a simpler method without plyvel.
    """
    print(f"Looking for OneTab data in: {leveldb_path}")
    
    # Pattern to find URLs and potential OneTab data
    url_pattern = re.compile(r'https?://[^\s"\']+')
    onetab_pattern = re.compile(r'tabGroups')
    
    urls = []
    tab_groups = []
    
    # Check if the directory exists
    if not os.path.isdir(leveldb_path):
        print(f"Error: Directory {leveldb_path} does not exist")
        return False
    
    # Find all LDB and LOG files in the directory
    ldb_files = list(Path(leveldb_path).glob("*.ldb")) + list(Path(leveldb_path).glob("*.log"))
    
    if not ldb_files:
        print("No .ldb or .log files found in the specified directory")
        return False
    
    print(f"Found {len(ldb_files)} database files to examine")
    
    # Use strings command to extract text from binary files
    for ldb_file in ldb_files:
        print(f"Examining file: {ldb_file}")
        try:
            # Use strings command to extract text content
            result = subprocess.run(['strings', str(ldb_file)], capture_output=True, text=True)
            content = result.stdout
            
            # Look for OneTab data structures
            if 'tabGroups' in content:
                print(f"Found potential OneTab data in {ldb_file}")
                # Try to extract JSON structures
                json_matches = re.finditer(r'({[^{]*?"tabGroups"[^}]*?})', content)
                for match in json_matches:
                    try:
                        json_str = match.group(1)
                        # Clean up the JSON string if needed
                        json_str = re.sub(r'\\+', '\\\\', json_str)
                        data = json.loads(json_str)
                        if 'tabGroups' in data:
                            tab_groups.append(data)
                            print(f"Found TabGroups data with {len(data['tabGroups'])} groups")
                    except json.JSONDecodeError as e:
                        # If JSON parsing fails, try to extract URLs
                        print(f"JSON decode error: {e}, extracting URLs directly")
                
            # Extract URLs
            url_matches = url_pattern.findall(content)
            if url_matches:
                for url in url_matches:
                    if url not in urls:
                        urls.append(url)
                print(f"Found {len(url_matches)} URLs in {ldb_file}")
                
        except Exception as e:
            print(f"Error processing file {ldb_file}: {e}")
    
    # Process the extracted data
    all_urls = []
    
    # Get URLs from tab groups
    for group_data in tab_groups:
        for group in group_data.get('tabGroups', []):
            if isinstance(group, dict) and 'tabs' in group:
                for tab in group.get('tabs', []):
                    if isinstance(tab, dict) and 'url' in tab:
                        all_urls.append({
                            'url': tab['url'],
                            'title': tab.get('title', ''),
                            'group': group.get('name', 'Unnamed Group')
                        })
    
    # Add URLs found via regex that aren't already in the list
    for url in urls:
        if url not in [entry['url'] for entry in all_urls]:
            all_urls.append({
                'url': url,
                'title': '',
                'group': 'Unknown Group'
            })
    
    # Save results
    if all_urls:
        if output_file:
            with open(output_file, 'w') as f:
                # Write as JSON only
                json.dump(all_urls, f, indent=2)
                
            # Write plain text URLs to a separate file
            txt_file = output_file.replace('.json', '.txt')
            with open(txt_file, 'w') as f:
                for entry in all_urls:
                    f.write(f"{entry['url']} - {entry['title']}\n")
                
            print(f"Extracted {len(all_urls)} URLs, saved to {output_file} and {txt_file}")
        else:
            print("\nExtracted URLs:")
            for entry in all_urls[:10]:  # Show only first 10 to avoid overwhelming output
                print(f"{entry['url']} - {entry['title']}")
            print(f"\nTotal: {len(all_urls)} URLs")
        return True, all_urls
    else:
        print("No OneTab URLs found.")
        return False, []

def export_to_html(urls, output_file):
    """
    Export the URLs to an HTML file that can be imported into bookmarks
    """
    html = """<!DOCTYPE NETSCAPE-Bookmark-file-1>
<META HTTP-EQUIV="Content-Type" CONTENT="text/html; charset=UTF-8">
<TITLE>Bookmarks</TITLE>
<H1>Bookmarks</H1>
<DL><p>
    <DT><H3>Recovered OneTab URLs</H3>
    <DL><p>
"""
    
    # Group by the 'group' field
    groups = {}
    for entry in urls:
        group = entry.get('group', 'Unknown Group')
        if group not in groups:
            groups[group] = []
        groups[group].append(entry)
    
    # Create HTML
    for group_name, entries in groups.items():
        html += f'        <DT><H3>{group_name}</H3>\n        <DL><p>\n'
        for entry in entries:
            title = entry.get('title', entry['url'])
            if not title:
                title = entry['url']
            html += f'            <DT><A HREF="{entry["url"]}">{title}</A>\n'
        html += '        </DL><p>\n'
    
    html += """    </DL><p>
</DL><p>
"""
    
    with open(output_file, 'w') as f:
        f.write(html)
    
    print(f"Exported {sum(len(entries) for entries in groups.values())} URLs to {output_file}")
    return True

def main():
    parser = argparse.ArgumentParser(description='Extract OneTab data from LevelDB')
    parser.add_argument('--path', type=str, help='Path to the LevelDB directory', 
                        default=os.path.expanduser('~/.config/google-chrome/Default/Local Extension Settings/chphlpgkkbolifaimnlloiipkdnihall/'))
    parser.add_argument('--output', type=str, help='Output file to save URLs', default='onetab_urls.json')
    parser.add_argument('--html', type=str, help='Output HTML file for bookmark import', default='onetab_bookmarks.html')
    args = parser.parse_args()
    
    # Extract data from LevelDB
    success, urls = extract_onetab_data_from_files(args.path, args.output)
    
    if success:
        # Export to HTML for bookmark import
        export_to_html(urls, args.html)
        
        print("\nRecovery completed successfully!")
        print(f"JSON data saved to: {args.output}")
        print(f"HTML bookmarks file saved to: {args.html}")
        print("\nYou can import the HTML file into Chrome or Firefox bookmarks:")
        print("Chrome: Bookmarks -> Import bookmarks and settings -> Bookmarks HTML file")
        print("Firefox: Bookmarks -> Manage Bookmarks -> Import and Backup -> Import Bookmarks from HTML")
    else:
        print("\nUnable to extract OneTab data.")

if __name__ == "__main__":
    main()
