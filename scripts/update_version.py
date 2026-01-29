#!/usr/bin/env python3
"""Version update script for the project."""

import json
import re
import subprocess
import sys
from pathlib import Path


def update_version(new_version: str) -> None:
    """Update version in all relevant files."""
    root = Path(__file__).parent.parent

    # Update config.yaml
    config_file = root / "public-dashboard" / "config.yaml"
    content = config_file.read_text()
    content = re.sub(r'version: "[^"]*"', f'version: "{new_version}"', content)
    config_file.write_text(content)

    # Update package.json
    package_file = root / "public-dashboard" / "rootfs" / "var" / "www" / "package.json"
    with package_file.open() as f:
        data = json.load(f)
    data["version"] = new_version
    with package_file.open("w") as f:
        json.dump(data, f, indent=2)

    subprocess.run(["uv", "version", new_version], cwd=root, check=True)  # noqa: S603, S607

    # Update pyproject.toml using uv
    pyproject_dir = root / "public-dashboard" / "rootfs" / "app"
    subprocess.run(["uv", "version", new_version], cwd=pyproject_dir, check=True)  # noqa: S603, S607

    print(f"Updated version to {new_version}")  # noqa: T201


if __name__ == "__main__":
    if len(sys.argv) != 2:  # noqa: PLR2004
        print("Usage: python update_version.py <version>")  # noqa: T201
        sys.exit(1)

    update_version(sys.argv[1])
