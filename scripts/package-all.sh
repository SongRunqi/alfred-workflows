#!/bin/bash
# package-all.sh — Build every workflow folder into an installable
# .alfredworkflow at the repo root.
#
# Used by the GitHub Actions release pipeline AND locally (same output,
# deterministic): zips the *contents* of each workflow folder (info.plist
# must sit at the archive root), excludes dev-only files, keeps exec bits,
# and verifies each package's info.plist parses.
#
# Usage:  bash scripts/package-all.sh   (from anywhere; resolves the repo root)

set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT"

# workflow folder|packaged file name (plist `name` is the display name;
# the .alfredworkflow file name matches the repo's existing artifacts).
# Plain parallel list — macOS ships bash 3.2, which has no associative arrays.
PACKAGES=(
  "Homebrew Manager|Homebrew Manager"
  "netease-music-controls|NetEase Music Controls"
  "Glide|Glide"
  "PiHop|PiHop"
  "System Settings|Settings"
)

# Dev files that must never ship inside a package.
EXCLUDE=(
  -x "*.pyc"
  -x "__pycache__/*"
  -x ".DS_Store"
  -x ".ruff_cache/*"
  -x "*.swift"        # engine sources (window_control.swift, make_icons.swift)
  -x "build_plist.py" # plist generator
  -x "pack.sh"        # Glide's local release packer
  -x "README.md"      # repo-facing docs; the plist `readme` field ships instead
)

for entry in "${PACKAGES[@]}"; do
  dir="${entry%%|*}"
  name="${entry#*|}"
  [[ -d "$dir" ]] || { echo "SKIP (no dir): $dir"; continue; }
  [[ -f "$dir/info.plist" ]] || { echo "SKIP (no info.plist): $dir"; continue; }

  out="$ROOT/$name.alfredworkflow"
  rm -f "$out"
  (cd "$dir" && zip -q -r -X "$out" . "${EXCLUDE[@]}")
  echo "packed: $name.alfredworkflow ($(du -h "$out" | cut -f1))"
done

echo
echo "=== verify every package ==="
for pkg in "$ROOT"/*.alfredworkflow; do
  # parse the embedded info.plist to catch broken archives early
  unzip -p "$pkg" info.plist | python3 -c "
import plistlib, sys
d = plistlib.loads(sys.stdin.buffer.read())
assert d.get('name'), 'missing name'
print(f\"  OK  {d['name']}  v{d.get('version', '?')}\")
" || { echo "  FAIL $pkg"; exit 1; }
done
echo "All packages verified."
