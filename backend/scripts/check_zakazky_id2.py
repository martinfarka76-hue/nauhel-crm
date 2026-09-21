import sys
sys.path.insert(0, ".")
import httpx
from app.core import sharepoint

site_id, drive_id = sharepoint._get_site_and_drive()
folder_id = "0176HGS3UWYFYSCR5PBFC22IWRNR5QLUG7"

print("--- 1) GET primo podle ID ---")
resp = httpx.get(
    f"{sharepoint.GRAPH_BASE}/drives/{drive_id}/items/{folder_id}",
    headers=sharepoint._headers(),
    timeout=15.0,
)
print("Status:", resp.status_code)
print(resp.text[:500])

print()
print("--- 2) Vypis childCount pres root/children (hledani 03_Zakazky) ---")
resp2 = httpx.get(
    f"{sharepoint.GRAPH_BASE}/drives/{drive_id}/root/children",
    headers=sharepoint._headers(),
    timeout=15.0,
)
print("Status:", resp2.status_code)
if resp2.status_code == 200:
    for item in resp2.json().get("value", []):
        print(" -", item.get("name"), "| id:", item.get("id"))
else:
    print(resp2.text[:500])
