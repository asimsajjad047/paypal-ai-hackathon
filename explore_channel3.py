import json
import os
from dotenv import load_dotenv
from channel3_sdk import Channel3

load_dotenv()

# Pass the key (and UK settings) explicitly: the SDK reads env vars when it's
# imported, which happens BEFORE load_dotenv() runs.
client = Channel3(api_key=os.getenv("CHANNEL3_API_KEY"), country="GB", currency="GBP")

results = client.products.search(query="RTX 4070 graphics card")

# search() returns a pager; the raw first page is in results.response
page = results.response
data = page.model_dump() if hasattr(page, "model_dump") else page

with open("sample_channel3.json", "w") as f:
    json.dump(data, f, indent=2, default=str)

print("Saved to sample_channel3.json")
print("Top-level keys:", list(data.keys()) if isinstance(data, dict) else type(data))
for product in (results.items or [])[:3]:
    for offer in product.offers or []:
        print(f"£{offer.price.price:>8.2f} {offer.price.currency}  {offer.domain:<25} {product.title[:50]}")
