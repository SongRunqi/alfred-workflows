#!/usr/bin/env python3
"""Alfred Script Filter — NetEase Music quick controls.

Prints a JSON array of Alfred items for playback control.
Query argument filters the list case-insensitively.
"""

import json
import sys

ACTIONS = [
    {"title": "▶️  Play / Pause", "arg": "toggle-play"},
    {"title": "⏭  Next Track", "arg": "next-track"},
    {"title": "⏮  Previous Track", "arg": "previous-track"},
    {"title": "🔊  Volume Up", "arg": "turn-up-volume"},
    {"title": "🔉  Volume Down", "arg": "turn-down-volume"},
    {"title": "❤️  Like / Dislike", "arg": "like"},
    {"title": "🔀  Toggle Shuffle", "arg": "toggle-shuffle"},
    {"title": "🔁  Repeat One", "arg": "repeat-one"},
]

ICON = {"path": "icon.png"}


def main() -> None:
    query = (sys.argv[1] if len(sys.argv) > 1 else "").strip().lower()

    items = []
    for a in ACTIONS:
        if query and query not in a["title"].lower():
            continue
        items.append(
            {
                "uid": a["arg"],
                "title": a["title"],
                "arg": a["arg"],
                "autocomplete": a["title"],
                "icon": ICON,
                "valid": True,
            }
        )

    if not items:
        items = [
            {
                "title": "No matching controls",
                "subtitle": f"Nothing matched “{query}”",
                "valid": False,
            }
        ]

    sys.stdout.write(json.dumps({"items": items}))


if __name__ == "__main__":
    try:
        main()
    except Exception as exc:
        sys.stderr.write(f"filter.py error: {exc}\n")
        sys.stdout.write(
            json.dumps(
                {"items": [{"title": "Error", "subtitle": str(exc), "valid": False}]}
            )
        )
