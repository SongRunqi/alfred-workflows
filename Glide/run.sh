#!/bin/bash
# Window Control runner: forwards the action id to the geometry engine.
# The engine prints an error message on failure (surfaced as a notification)
# and nothing on success. The workflow-config "animate" checkbox controls
# smooth animation (default on; "0" snaps instantly).
cd "$(dirname "$0")" || exit 1
exec ./window_control "$1" "${animate:-1}"
