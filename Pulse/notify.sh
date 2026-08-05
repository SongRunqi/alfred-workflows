#!/bin/sh
# Hyper+U entry: silent check → notification summary.
exec "$(dirname "$0")/pulse.py" notify
