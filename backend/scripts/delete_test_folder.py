import sys
sys.path.insert(0, ".")
import httpx
from app.core import sharepoint

drive_id = "b!rfzfz6rBwUaSmGNlemRLqYxe5arwcR1Nk2sBu0ZClRHG895YSnouTrCq4ICaZb4r"
folder_id = "0176HGS3TGCNQHWLWKF5HIW3MZ6F4Z5MQ2"

resp = httpx.delete(
    f"{sharepoint.GRAPH_BASE}/drives/{drive_id}/items/{folder_id}",
    headers=sharepoint._headers(),
    timeout=15.0,
)
print("Status:", resp.status_code)
print("Body:", resp.text[:300] if resp.text else "(prazdne - OK)")
