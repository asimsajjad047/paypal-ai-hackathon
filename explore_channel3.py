import json
import os
from dotenv import load_dotenv
from channel3_sdk import Channel3

load_dotenv()

client = Channel3(
    api_key=os.getenv("CHANNEL3_API_KEY"),
    country="GB",
    currency="GBP",
)

results = client.products.search(query="RTX 4070 graphics card", limit=5)

data = results.response.model_dump()

with open("sample_channel3.json", "w") as f:
    json.dump(data, f, indent=2, default=str)

print("Saved to sample_channel3.json")
print("Top-level keys:", list(data.keys()))
print("Number of products:", len(data["products"]))