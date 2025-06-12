#!/usr/bin/env python3
import json
import sys

data = json.load(sys.stdin)
print("Current unlocked AI child topics:")
for item in data["progress"]:
    if item["topic"]["name"] != "Artificial Intelligence":
        print(f"- {item['topic']['name']}")