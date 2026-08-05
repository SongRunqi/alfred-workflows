#!/bin/sh
# Script Filter entry: argv[1] is the raw query typed after `app`.
exec "$(dirname "$0")/app.py" query "$1"
