#!/bin/bash
# App Launcher release packer.
#
# Regenerates info.plist, zips the runtime files into
# ../App Launcher.alfredworkflow, and verifies every executable
# keeps its +x bit inside the package (Alfred fails with "launch
# path not accessible" otherwise).
#
# Usage: ./pack.sh        (from this folder, or anywhere — resolves itself)

set -euo pipefail
cd "$(dirname "$0")"

NAME="App Launcher"
OUT="$(cd .. && pwd)/$NAME.alfredworkflow"

# --- 1. rebuild plist + icon -------------------------------------------------
python3 build_plist.py
python3 make_icon.py

# --- 2. ensure executables ------------------------------------------------
chmod +x app.py launch.sh launchq.sh filter.sh

# --- 3. pack ----------------------------------------------------------------
rm -f "$OUT"
zip -q -r -X "$OUT" app.py launch.sh launchq.sh filter.sh icon.png info.plist

echo "✓ Packed: $OUT"
echo
echo "Contents & permissions:"
TMPU="$(mktemp -d)"
unzip -q "$OUT" -d "$TMPU"
(cd "$TMPU" && ls -lR | grep -v '^total')
rm -rf "$TMPU"

# --- 4. verify +x bits ------------------------------------------------------
for f in app.py launch.sh launchq.sh filter.sh; do
	TMPU="$(mktemp -d)"
	unzip -q "$OUT" -d "$TMPU"
	[[ -x "$TMPU/$f" ]] || {
		echo "ERROR: $f lost +x in package!"
		exit 1
	}
	rm -rf "$TMPU"
done

# --- 5. verify plist ---------------------------------------------------------
TMPU="$(mktemp -d)"
unzip -q "$OUT" -d "$TMPU"
plutil -lint "$TMPU/info.plist"
rm -rf "$TMPU"

echo
echo "✓ All executables keep +x inside the package. Ready to release."
