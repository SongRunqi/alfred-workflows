#!/usr/bin/env python3
"""Static action list for the Glide Script Filter.

Alfred filters the results itself (alfredfiltersresults), so the query is
ignored here. Each item's arg is the action id routed by the Conditional.
"""

import json

ACTIONS = [
    ("max", "Maximize", "Fill the visible screen", "icons/max.png"),
    ("reasonable", "Reasonable", "Two-thirds width, centered", "icons/reasonable.png"),
    ("center", "Center", "Keep size, center on screen", "icons/center.png"),
    ("tl", "Top Left", "Top-left quarter", "icons/tl.png"),
    ("tr", "Top Right", "Top-right quarter", "icons/tr.png"),
    ("bl", "Bottom Left", "Bottom-left quarter", "icons/bl.png"),
    ("br", "Bottom Right", "Bottom-right quarter", "icons/br.png"),
    ("lh", "Left Half", "Left half of the screen", "icons/lh.png"),
    ("rh", "Right Half", "Right half of the screen", "icons/rh.png"),
    ("l3", "Left Third", "Left third of the screen", "icons/l3.png"),
    ("c3", "Center Third", "Center third of the screen", "icons/c3.png"),
    ("r3", "Right Third", "Right third of the screen", "icons/r3.png"),
]

# No uid on purpose: the fixed palette order must survive Alfred's learning.
items = [
    {
        "title": title,
        "subtitle": subtitle,
        "arg": arg,
        "icon": {"path": icon},
    }
    for arg, title, subtitle, icon in ACTIONS
]

print(json.dumps({"items": items}))
