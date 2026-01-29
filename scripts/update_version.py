#!/usr/bin/env python3
import sys
import re
import json
from pathlib import Path

def update_version(new_version):
    root = Path(__file__).parent.parent
    
    # Update config.yaml
    config_file = root / "public-dashboard" / "config.yaml"
    content = config_file.read_text()
    content = re.sub(r'version: "[^"]*"', f'version: "{new_version}"', content)
    config_file.write_text(content)
    
    # Update package.json
    package_file = root / "public-dashboard" / "rootfs" / "var" / "www" / "package.json"
    with open(package_file, 'r') as f:
        data = json.load(f)
    data['version'] = new_version
    with open(package_file, 'w') as f:
        json.dump(data, f, indent=2)
    
    print(f"Updated version to {new_version}")

if __name__ == "__main__":
    if len(sys.argv) != 2:
        print("Usage: python update_version.py <version>")
        sys.exit(1)
    update_version(sys.argv[1])