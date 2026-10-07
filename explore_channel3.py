import json
from dotenv import load_dotenv
from channel3_sdk import Channel3

load_dotenv()

client = Channel3()

results = client.products.search(query="RTX 4070 graphics card")

data = results.model_dump() if hasattr(results, "model_dump") else results

with open("sample_channel3.json", "w") as f:
    json.dump(data, f, indent=2, default=str)

print("Saved to sample_channel3.json")
print("Top-level keys:", list(data.keys()) if isinstance(data, dict) else type(data))