import sys
sys.path.insert(0, ".")
import httpx
from app.core import sharepoint

site_id, drive_id = sharepoint._get_site_and_drive()
print("drive_id:", drive_id)

resp = httpx.get(
    f"{sharepoint.GRAPH_BASE}/drives/{drive_id}/root:/03_Zakázky",
    headers=sharepoint._headers(),
    timeout=15.0,
)
print("Status:", resp.status_code)
print("Odpoved:", resp.json())
