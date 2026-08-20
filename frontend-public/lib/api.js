const API_URL = process.env.NEXT_PUBLIC_API_URL || "http://localhost:18080";

export async function fetchPublicDocument(token) {
  const res = await fetch(`${API_URL}/public/documents/${token}`);
  if (!res.ok) {
    throw new Error(res.status === 404 ? "not_found" : "error");
  }
  return res.json();
}

export function sendViewDuration(token, viewId, durationSeconds) {
  const url = `${API_URL}/public/documents/${token}/views/${viewId}`;
  const payload = JSON.stringify({ duration_seconds: durationSeconds });

  // sendBeacon je spolehlivější při zavírání stránky než fetch, ale
  // nepodporuje PATCH ani vlastní content-type - použijeme proto fetch
  // s keepalive: true, což zajišťuje podobnou spolehlivost při unloadu.
  try {
    fetch(url, {
      method: "PATCH",
      headers: { "Content-Type": "application/json" },
      body: payload,
      keepalive: true,
    });
  } catch {
    // Best-effort - pokud selže, nechceme blokovat odchod ze stránky
  }
}
