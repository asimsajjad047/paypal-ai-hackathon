import json

with open("sample_channel3.json") as f:
    data = json.load(f)

first = data["products"][0]
print("Title:", first["title"])
print("Number of offers:", len(first["offers"] or []))