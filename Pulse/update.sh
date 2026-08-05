#!/bin/sh
# Update entry: $1 = "<name>|<url>|<sha256>" | "all" | "dl|<name>|<url>|<sha256>"
# ("dl|" prefix = ⌘-Enter → download only, no import dialog).
case "$1" in
dl\|*) exec "$(dirname "$0")/pulse.py" download "${1#dl|}" ;;
*) exec "$(dirname "$0")/pulse.py" update "$1" ;;
esac
