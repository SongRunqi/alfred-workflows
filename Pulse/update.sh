#!/bin/sh
# Update entry: $1 = "<name>|<url>|<sha256>" | "all" | "dl|<…>" | "refresh"
# ("dl|" prefix = ⌘-Enter → download only, no import dialog; "refresh" =
# ↻ row → force a fresh check, then reopen the list via alfred://search).
case "$1" in
dl\|*) exec "$(dirname "$0")/pulse.py" download "${1#dl|}" ;;
refresh)
	"$(dirname "$0")/pulse.py" refresh
	open -a "Alfred 5" "alfred://search/update"
	;;
*) exec "$(dirname "$0")/pulse.py" update "$1" ;;
esac
