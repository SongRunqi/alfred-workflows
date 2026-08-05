#!/bin/bash
# Launch-or-toggle for the configurable slots and the `app` menu.
#
# $1 is one of:
#   terminal              → open $TERMINAL_APP  (workflow config popup)
#   browser               → open $BROWSER_APP   (workflow config popup)
#   <App Name>            → open that app
#   <App Name>|<path>…    → open app with file/folder arguments
#
# Toggle: if the target app is already frontmost, hide it (same behaviour as
# the old Launch Apps/Files objects). Frontmost detection via lsappinfo
# (no permission); hiding via System Events (one-time Automation prompt).

set -u
arg="${1:-}"

case "$arg" in
    terminal) app="${TERMINAL_APP:-iTerm}";      files="" ;;
    browser)  app="${BROWSER_APP:-Google Chrome}"; files="" ;;
    *)        app="${arg%%|*}"; files="${arg#*|}"
              [ "$files" = "$arg" ] && files="" ;;
esac

if [ -n "${APP_LAUNCH_DRY:-}" ]; then
    echo "[dry] app=$app files=$files"
    exit 0
fi

# expand a leading ~ in file args (open does not expand it after variable use)
[ -n "$files" ] && files="$(printf '%s' "$files" | sed "s|^~|$HOME|")"

# toggle: hide when already frontmost
front_asn="$(lsappinfo front 2>/dev/null || true)"
front_bid=""
if [ -n "$front_asn" ]; then
    front_bid="$(lsappinfo info -only bundleid "$front_asn" 2>/dev/null \
        | sed -n 's/.*"CFBundleIdentifier"="\([^"]*\)".*/\1/p')"
fi
target_bid="$(mdls -name kMDItemCFBundleIdentifier -raw "/Applications/${app}.app" 2>/dev/null | tr -d '"' || true)"
if [ -n "$front_bid" ] && [ -n "$target_bid" ] && [ "$front_bid" = "$target_bid" ]; then
    osascript -e "tell application \"System Events\" to set visible of (first process whose bundle identifier is \"$target_bid\") to false" >/dev/null 2>&1 \
        && exit 0
fi

exec open -a "$app" $files
