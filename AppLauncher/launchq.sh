#!/bin/sh
# Selected-text query entry (⌥⇧S → Easydict): passes the selection to the
# registry entry bound to key "s" as its query text.
exec "$(dirname "$0")/app.py" launch s "$1"
