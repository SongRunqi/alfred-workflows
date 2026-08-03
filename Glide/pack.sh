#!/bin/bash
# Glide release packer.
#
# Builds a slim, install-ready Glide.alfredworkflow:
#   - includes only runtime files (scripts, engine, icons, plist)
#   - excludes dev files (build_plist.py, make_icons.swift, *.swift, README…)
#   - ensures +x on all executables so Alfred never hits
#     "launch path not accessible" after import
#
# Usage:  ./pack.sh        (from this folder, or anywhere — resolves itself)
#
# Optional: ./pack.sh --universal   rebuilds window_control as a universal
#              (arm64 + x86_64, macOS 13+) binary before packing. Requires
#              Xcode command line tools (swiftc).

set -euo pipefail
cd "$(dirname "$0")"

NAME="Glide"
OUT="$(cd .. && pwd)/$NAME.alfredworkflow" # absolute, survives cd

# --- 1. rebuild universal engine (optional) ---------------------------------
if [[ "${1:-}" == "--universal" ]]; then
	echo "→ Rebuilding universal window_control (arm64 + x86_64, macOS 13+)…"
	TMPB="$(mktemp -d)"
	swiftc -O -framework AppKit -framework ApplicationServices \
		-target arm64-apple-macosx13.0 window_control.swift -o "$TMPB/wc_arm64"
	swiftc -O -framework AppKit -framework ApplicationServices \
		-target x86_64-apple-macosx13.0 window_control.swift -o "$TMPB/wc_x86_64"
	lipo -create -output window_control "$TMPB/wc_arm64" "$TMPB/wc_x86_64"
	echo "✓ window_control rebuilt: $(lipo -info window_control | sed 's/.*are: //')"
fi

# --- 2. executable bits (this is what broke installs before) ----------------
chmod +x actions.py run.sh window_control

# --- 3. stage only runtime files --------------------------------------------
STAGE="$(mktemp -d)"
trap 'rm -rf "$STAGE" "${TMPB:-}"' EXIT

cp info.plist icon.png actions.py run.sh window_control "$STAGE/"
cp -R icons "$STAGE/"

# --- 4. zip contents with permissions preserved -----------------------------
cd "$STAGE"
rm -f "$OUT"
zip -q -r -X "$OUT" .
cd - >/dev/null

# --- 5. verify ---------------------------------------------------------------
echo "✓ Packed: $OUT"
echo
echo "Contents & permissions:"
TMPU="$(mktemp -d)"
unzip -q "$OUT" -d "$TMPU"
(cd "$TMPU" && ls -lR | grep -v '^total')
rm -rf "$TMPU"

# fail loudly if any executable lost its +x bit inside the zip
for f in actions.py run.sh window_control; do
	TMPU="$(mktemp -d)"
	unzip -q "$OUT" -d "$TMPU"
	[[ -x "$TMPU/$f" ]] || {
		echo "ERROR: $f lost +x in package!"
		exit 1
	}
	rm -rf "$TMPU"
done
echo
echo "✓ All executables keep +x inside the package. Ready to release."
