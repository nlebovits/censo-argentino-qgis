#!/usr/bin/env python3
"""
Version bumping script for censo-argentino-qgis plugin.

Usage:
    python scripts/bump_version.py 0.3.0
    python scripts/bump_version.py --patch  # Bumps patch version (0.2.0 -> 0.2.1)
    python scripts/bump_version.py --minor  # Bumps minor version (0.2.0 -> 0.3.0)
    python scripts/bump_version.py --major  # Bumps major version (0.2.0 -> 1.0.0)
"""

import re
import sys
from pathlib import Path
from datetime import date


def get_current_version():
    """Read current version from metadata.txt."""
    metadata_path = Path(__file__).parent.parent / "metadata.txt"
    content = metadata_path.read_text()
    match = re.search(r'^version=(.+)$', content, re.MULTILINE)
    if match:
        return match.group(1)
    raise ValueError("Could not find version in metadata.txt")


def bump_version_component(version, component):
    """Bump major, minor, or patch component."""
    major, minor, patch = map(int, version.split('.'))

    if component == 'major':
        return f"{major + 1}.0.0"
    elif component == 'minor':
        return f"{major}.{minor + 1}.0"
    elif component == 'patch':
        return f"{major}.{minor}.{patch + 1}"
    else:
        raise ValueError(f"Unknown component: {component}")


def update_file(file_path, pattern, replacement):
    """Update a file using regex pattern and replacement."""
    content = file_path.read_text()
    updated = re.sub(pattern, replacement, content, flags=re.MULTILINE)

    if content == updated:
        print(f"⚠️  Warning: No changes made to {file_path.name}")
        return False

    file_path.write_text(updated)
    print(f"✓ Updated {file_path.name}")
    return True


def bump_version(new_version):
    """Update version across all project files."""
    root = Path(__file__).parent.parent
    today = date.today().isoformat()

    files_updated = []

    # Update metadata.txt
    metadata_path = root / "metadata.txt"
    if update_file(metadata_path, r'^version=.+$', f'version={new_version}'):
        files_updated.append('metadata.txt')

    # Update pyproject.toml
    pyproject_path = root / "pyproject.toml"
    if update_file(pyproject_path, r'^version = ".+"$', f'version = "{new_version}"'):
        files_updated.append('pyproject.toml')

    # Update CHANGELOG.md - add Unreleased section if not exists
    changelog_path = root / "docs" / "CHANGELOG.md"
    changelog_content = changelog_path.read_text()

    # Check if there's an [Unreleased] section to convert
    if '[Unreleased]' in changelog_content:
        updated = changelog_content.replace(
            '## [Unreleased]',
            f'## [{new_version}] - {today}'
        )
        changelog_path.write_text(updated)
        print(f"✓ Updated CHANGELOG.md (converted Unreleased to {new_version})")
        files_updated.append('docs/CHANGELOG.md')
    else:
        print(f"ℹ️  CHANGELOG.md has no [Unreleased] section to convert")
        print(f"   Manually add version {new_version} entry if needed")

    return files_updated


def main():
    if len(sys.argv) != 2:
        print(__doc__)
        print(f"\nCurrent version: {get_current_version()}")
        sys.exit(1)

    arg = sys.argv[1]

    # Determine new version
    if arg in ('--major', '--minor', '--patch'):
        current = get_current_version()
        component = arg[2:]  # Remove '--' prefix
        new_version = bump_version_component(current, component)
        print(f"Bumping {component}: {current} → {new_version}")
    else:
        # Validate version format
        if not re.match(r'^\d+\.\d+\.\d+$', arg):
            print(f"Error: Invalid version format '{arg}'")
            print("Expected format: X.Y.Z (e.g., 0.3.0)")
            sys.exit(1)
        new_version = arg
        print(f"Setting version to: {new_version}")

    # Perform version bump
    files_updated = bump_version(new_version)

    if files_updated:
        print(f"\n✓ Version bumped to {new_version}")
        print(f"  Updated: {', '.join(files_updated)}")
        print(f"\nNext steps:")
        print(f"  1. Review changes: git diff")
        print(f"  2. Commit: git add -A && git commit -m 'Bump version to {new_version}'")
        print(f"  3. Tag: git tag v{new_version}")
        print(f"  4. Push: git push && git push --tags")
    else:
        print("\n⚠️  No files were updated")
        sys.exit(1)


if __name__ == '__main__':
    main()
