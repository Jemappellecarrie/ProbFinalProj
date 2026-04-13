import os
import requests

token = os.getenv("LITELLM_TOKEN")
url = "https://litellm.oit.duke.edu/v1/models"

resp = requests.get(
    url,
    headers={"Authorization": f"Bearer {token}"}
)
resp.raise_for_status()

for model in resp.json()["data"]:
    print(model["id"])