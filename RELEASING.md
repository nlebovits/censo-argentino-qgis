# Release Process

This document describes how to create a new release of the censo-argentino-qgis plugin.

## Prerequisites

- All changes committed and pushed to `main`
- All tests passing (`uv run pytest`)
- CHANGELOG.md updated with new version

## Release Steps

### 1. Update Version

Use the version bumping script:

```bash
# Bump to specific version
python3 scripts/bump_version.py 0.4.0

# Or use semantic versioning shortcuts
python3 scripts/bump_version.py --patch  # 0.3.0 -> 0.3.1
python3 scripts/bump_version.py --minor  # 0.3.0 -> 0.4.0
python3 scripts/bump_version.py --major  # 0.3.0 -> 1.0.0
```

This updates:
- `metadata.txt`
- `pyproject.toml`
- `docs/CHANGELOG.md` (if [Unreleased] section exists)

### 2. Review Changes

```bash
git diff
```

Verify version numbers are correct in all files.

### 3. Commit and Tag

```bash
# Commit version bump
git add -A
git commit -m "Bump version to 0.4.0"

# Create git tag
git tag v0.4.0

# Push everything
git push
git push --tags
```

### 4. Automated Release

The GitHub Actions workflow (`.github/workflows/release.yml`) will automatically:

1. Verify version consistency across files
2. Extract changelog notes for this version
3. Create a plugin ZIP file with:
   - All Python files
   - UI files (*.ui)
   - Icons (*.png)
   - metadata.txt
   - LICENSE
   - README.md
4. Create a GitHub Release with:
   - Changelog notes
   - Plugin ZIP as downloadable artifact

### 5. Verify Release

1. Go to: https://github.com/nlebovits/censo-argentino-qgis/releases
2. Verify the release was created
3. Download the ZIP file
4. Test the plugin in QGIS:
   ```bash
   # Extract and install
   unzip censo-argentino-qgis-0.4.0.zip
   # Copy to QGIS plugins directory
   ```

### 6. (Optional) Publish to QGIS Plugin Repository

To make the plugin available via QGIS Plugin Manager:

1. Create account at: https://plugins.qgis.org/
2. Go to: https://plugins.qgis.org/plugins/add/
3. Upload the ZIP file from the GitHub release
4. Fill in additional metadata if required
5. Submit for review

## Version Numbering

Follow semantic versioning (MAJOR.MINOR.PATCH):

- **MAJOR**: Breaking changes, major feature overhauls
- **MINOR**: New features, significant improvements
- **PATCH**: Bug fixes, minor improvements

Examples:
- `0.3.0 -> 0.3.1`: Bug fix release
- `0.3.0 -> 0.4.0`: New features added
- `0.3.0 -> 1.0.0`: Stable release with breaking changes

## Changelog Format

Follow the format in `docs/CHANGELOG.md`:

```markdown
## [0.4.0] - 2025-01-27

### Agregado
- New feature descriptions

### Mejorado
- Improvements and enhancements

### Corregido
- Bug fixes

### Técnico
- Technical/internal changes
```

Categories:
- **Agregado**: New features
- **Mejorado**: Improvements to existing features
- **Corregido**: Bug fixes
- **Eliminado**: Removed features
- **Técnico**: Technical changes, refactoring, dependencies

## Troubleshooting

### Release workflow failed

Check the workflow logs at:
https://github.com/nlebovits/censo-argentino-qgis/actions

Common issues:
- Version mismatch between tag and metadata.txt
- Missing changelog entry for the version
- ZIP creation failed (check file permissions)

### Version mismatch error

If the workflow reports version mismatch:

```bash
# Check current versions
grep '^version=' metadata.txt
grep '^version = ' pyproject.toml

# Re-run version bump
python3 scripts/bump_version.py 0.4.0
git add -A
git commit --amend --no-edit
git tag -d v0.4.0  # Delete old tag
git tag v0.4.0     # Create new tag
git push --force
git push --tags --force
```

## Manual Release (Fallback)

If GitHub Actions is unavailable, create release manually:

```bash
# Create plugin directory
mkdir -p /tmp/censo-argentino-qgis
cp *.py *.ui *.png metadata.txt LICENSE README.md /tmp/censo-argentino-qgis/

# Create ZIP
cd /tmp
zip -r censo-argentino-qgis-0.4.0.zip censo-argentino-qgis

# Upload to GitHub Releases manually
```
