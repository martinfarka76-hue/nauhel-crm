"use client";

import { useEffect, useState, useRef } from "react";
import Link from "next/link";
import { usePathname, useRouter } from "next/navigation";
import { isLoggedIn, clearToken, api } from "@/lib/api";

function formatNotifDate(iso) {
  const utcIso = iso.endsWith("Z") || iso.includes("+") ? iso : iso + "Z";
  return new Date(utcIso).toLocaleString("cs-CZ");
}

function BellIcon() {
  return (
    <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.8" strokeLinecap="round" strokeLinejoin="round">
      <path d="M18 8a6 6 0 0 0-12 0c0 7-3 9-3 9h18s-3-2-3-9" />
      <path d="M13.73 21a2 2 0 0 1-3.46 0" />
    </svg>
  );
}

function NauhelLogo({ height = 16 }) {
  return (
    <svg height={height} viewBox="202.875 256.25 417.375 52.625" style={{ color: "var(--ember-500)", display: "block" }}>
      <path transform="matrix(1,0,0,-1,365.4637,256.3749)" d="M0 0V-30.032C0-40.119 4.203-44.78 10.546-44.78 17.347-44.78 21.396-40.119 21.396-30.032V0H30.796V-29.42C30.796-45.315 22.619-52.345 10.24-52.345-1.681-52.345-9.399-45.697-9.399-29.497V0Z" fill="currentColor"/>
      <path transform="matrix(1,0,0,-1,238.6289,256.4994)" d="M0 0 .154-31.788-26.638-8.268-26.654-8.295-35.745 .082V-52.178H-26.324V-21.195L.214-44.259 .253-52.343 9.421-52.261V0Z" fill="currentColor"/>
      <path transform="matrix(1,0,0,-1,327.3455,308.8425)" d="M0 0-26.871 52.5-53.062 0H-42.078L-26.422 31.542-10.984 0Z" fill="currentColor"/>
      <path transform="matrix(1,0,0,-1,462.3477,256.4169)" d="M0 0V-22.064H-31.097V-31.484H0V-52.261H9.421V0Z" fill="currentColor"/>
      <path transform="matrix(1,0,0,-1,0,595.276)" d="M508.898 308.018H544.81607V317.439H508.898Z" fill="currentColor"/>
      <path transform="matrix(1,0,0,-1,0,595.276)" d="M508.898 329.438H544.81607V338.85899H508.898Z" fill="currentColor"/>
      <path transform="matrix(1,0,0,-1,0,595.276)" d="M508.898 286.556H544.81607V295.977H508.898Z" fill="currentColor"/>
      <path transform="matrix(1,0,0,-1,593.6667,299.2988)" d="M0 0V42.882H-9.421V0-9.379-9.421H26.497V0Z" fill="currentColor"/>
    </svg>
  );
}

function DashboardIcon() {
  return (
    <svg width="15" height="15" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.8" strokeLinecap="round" strokeLinejoin="round">
      <rect x="3" y="3" width="7" height="9" rx="1" />
      <rect x="14" y="3" width="7" height="5" rx="1" />
      <rect x="14" y="12" width="7" height="9" rx="1" />
      <rect x="3" y="16" width="7" height="5" rx="1" />
    </svg>
  );
}

function BuildingIcon() {
  return (
    <svg width="15" height="15" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.8" strokeLinecap="round" strokeLinejoin="round">
      <path d="M6 22V4a1 1 0 0 1 1-1h6a1 1 0 0 1 1 1v18" />
      <path d="M14 9h4a1 1 0 0 1 1 1v12" />
      <path d="M6 22h13" />
      <line x1="9" y1="6" x2="9" y2="6" />
      <line x1="9" y1="10" x2="9" y2="10" />
      <line x1="9" y1="14" x2="9" y2="14" />
      <line x1="13" y1="6" x2="13" y2="6" />
      <line x1="13" y1="10" x2="13" y2="10" />
      <line x1="13" y1="14" x2="13" y2="14" />
      <line x1="17" y1="13" x2="17" y2="13" />
      <line x1="17" y1="17" x2="17" y2="17" />
    </svg>
  );
}

function ContactsIcon() {
  return (
    <svg width="15" height="15" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.8" strokeLinecap="round" strokeLinejoin="round">
      <circle cx="12" cy="8" r="4" />
      <path d="M4 21c0-4 4-6 8-6s8 2 8 6" />
    </svg>
  );
}

function DocumentIcon() {
  return (
    <svg width="15" height="15" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.8" strokeLinecap="round" strokeLinejoin="round">
      <path d="M7 3h7l5 5v13a1 1 0 0 1-1 1H7a1 1 0 0 1-1-1V4a1 1 0 0 1 1-1z" />
      <path d="M14 3v5h5" />
      <line x1="9" y1="13" x2="15" y2="13" />
      <line x1="9" y1="17" x2="15" y2="17" />
    </svg>
  );
}

function ReportsIcon() {
  return (
    <svg width="15" height="15" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.8" strokeLinecap="round" strokeLinejoin="round">
      <line x1="18" y1="20" x2="18" y2="10" />
      <line x1="12" y1="20" x2="12" y2="4" />
      <line x1="6" y1="20" x2="6" y2="14" />
    </svg>
  );
}

function SettingsIcon() {
  return (
    <svg width="15" height="15" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.8" strokeLinecap="round" strokeLinejoin="round">
      <circle cx="12" cy="12" r="3" />
      <path d="M19.4 15a1.65 1.65 0 0 0 .33 1.82l.06.06a2 2 0 1 1-2.83 2.83l-.06-.06a1.65 1.65 0 0 0-1.82-.33 1.65 1.65 0 0 0-1 1.51V21a2 2 0 0 1-4 0v-.09A1.65 1.65 0 0 0 9 19.4a1.65 1.65 0 0 0-1.82.33l-.06.06a2 2 0 1 1-2.83-2.83l.06-.06a1.65 1.65 0 0 0 .33-1.82 1.65 1.65 0 0 0-1.51-1H3a2 2 0 0 1 0-4h.09A1.65 1.65 0 0 0 4.6 9a1.65 1.65 0 0 0-.33-1.82l-.06-.06a2 2 0 1 1 2.83-2.83l.06.06a1.65 1.65 0 0 0 1.82.33H9a1.65 1.65 0 0 0 1-1.51V3a2 2 0 0 1 4 0v.09a1.65 1.65 0 0 0 1 1.51 1.65 1.65 0 0 0 1.82-.33l.06-.06a2 2 0 1 1 2.83 2.83l-.06.06a1.65 1.65 0 0 0-.33 1.82V9a1.65 1.65 0 0 0 1.51 1H21a2 2 0 0 1 0 4h-.09a1.65 1.65 0 0 0-1.51 1z" />
    </svg>
  );
}

export default function ProtectedShell({ children }) {
  const router = useRouter();
  const pathname = usePathname();
  const [ready, setReady] = useState(false);
  const [user, setUser] = useState(null);

  const [unreadCount, setUnreadCount] = useState(0);
  const [notifications, setNotifications] = useState([]);
  const [showPanel, setShowPanel] = useState(false);
  const panelRef = useRef(null);

  useEffect(() => {
    if (!isLoggedIn()) {
      router.replace("/login");
      return;
    }
    api
      .get("/auth/me")
      .then((data) => {
        setUser(data);
        setReady(true);
      })
      .catch(() => {
        router.replace("/login");
      });
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  useEffect(() => {
    if (!ready) return;
    function pollUnread() {
      api
        .get("/notifications/unread-count")
        .then((data) => setUnreadCount(data.unread_count))
        .catch(() => {});
    }
    pollUnread();
    const interval = setInterval(pollUnread, 30000);
    return () => clearInterval(interval);
  }, [ready]);

  useEffect(() => {
    function handleClickOutside(e) {
      if (panelRef.current && !panelRef.current.contains(e.target)) {
        setShowPanel(false);
      }
    }
    if (showPanel) {
      document.addEventListener("mousedown", handleClickOutside);
      return () => document.removeEventListener("mousedown", handleClickOutside);
    }
  }, [showPanel]);

  function togglePanel() {
    if (!showPanel) {
      api
        .get("/notifications")
        .then(setNotifications)
        .catch(() => {});
    }
    setShowPanel(!showPanel);
  }

  async function handleMarkAllRead() {
    try {
      await api.post("/notifications/mark-all-read", {});
      setUnreadCount(0);
      setNotifications((prev) => prev.map((n) => ({ ...n, is_read: true })));
    } catch {
      // ignore
    }
  }

  async function handleNotificationClick(notification) {
    if (!notification.is_read) {
      try {
        await api.post(`/notifications/${notification.id}/read`, {});
        setUnreadCount((prev) => Math.max(0, prev - 1));
        setNotifications((prev) =>
          prev.map((n) => (n.id === notification.id ? { ...n, is_read: true } : n))
        );
      } catch {
        // ignore
      }
    }
    if (notification.deal_id) {
      window.location.href = `/deals/${notification.deal_id}`;
    }
  }

  if (!ready) {
    return <div style={{ padding: 40, color: "#8a8578" }}>Načítám…</div>;
  }

  function handleLogout() {
    clearToken();
    router.replace("/login");
  }

  const links = [
    { href: "/", label: "Přehled", Icon: DashboardIcon },
    { href: "/companies", label: "Firmy", Icon: BuildingIcon },
    { href: "/contacts", label: "Kontakty", Icon: ContactsIcon },
    { href: "/documents", label: "Dokumenty", Icon: DocumentIcon },
    { href: "/reports", label: "Reporty", Icon: ReportsIcon },
    { href: "/settings", label: "Nastavení", Icon: SettingsIcon },
  ];

  return (
    <div className="app-shell">
      <aside className="sidebar" style={{ position: "relative" }}>
        <div style={{ display: "flex", alignItems: "flex-start", justifyContent: "space-between", gap: 16, marginBottom: 4 }}>
          <div className="sidebar-brand" style={{ marginBottom: 0, flexShrink: 0 }}>
            <NauhelLogo height={14} />
          </div>

          <div ref={panelRef} style={{ position: "relative", flexShrink: 0 }}>
            <button
              onClick={togglePanel}
              aria-label="Notifikace"
              style={{
                position: "relative",
                background: "none",
                border: "none",
                color: showPanel ? "var(--ember-500)" : "var(--paper-200)",
                cursor: "pointer",
                padding: 4,
                display: "flex",
                alignItems: "center",
                justifyContent: "center",
              }}
            >
              <BellIcon />
              {unreadCount > 0 && (
                <span
                  style={{
                    position: "absolute",
                    top: -2,
                    right: -2,
                    width: 8,
                    height: 8,
                    borderRadius: "50%",
                    background: "var(--ember-500)",
                    border: "1.5px solid var(--char-950)",
                  }}
                />
              )}
            </button>

            {showPanel && (
              <div
                style={{
                  position: "absolute",
                  top: "calc(100% + 10px)",
                  left: 0,
                  width: 320,
                  maxHeight: 420,
                  overflowY: "auto",
                  background: "#fff",
                  border: "1px solid var(--line)",
                  borderRadius: 12,
                  boxShadow: "0 12px 32px rgba(14,12,9,0.18)",
                  zIndex: 60,
                }}
              >
                <div
                  style={{
                    display: "flex",
                    justifyContent: "space-between",
                    alignItems: "center",
                    padding: "12px 16px",
                    borderBottom: "1px solid var(--paper-200)",
                  }}
                >
                  <span style={{ fontSize: 13, fontWeight: 600, color: "var(--ink-900)" }}>
                    Notifikace{unreadCount > 0 ? ` · ${unreadCount}` : ""}
                  </span>
                  {unreadCount > 0 && (
                    <button
                      onClick={handleMarkAllRead}
                      style={{
                        background: "none",
                        border: "none",
                        color: "var(--ember-500)",
                        fontSize: 11.5,
                        cursor: "pointer",
                      }}
                    >
                      Označit vše přečtené
                    </button>
                  )}
                </div>
                {notifications.length === 0 ? (
                  <div style={{ padding: "24px 16px", fontSize: 13, color: "var(--ink-400)", textAlign: "center" }}>
                    Žádné notifikace
                  </div>
                ) : (
                  notifications.map((n) => (
                    <div
                      key={n.id}
                      onClick={() => handleNotificationClick(n)}
                      style={{
                        display: "flex",
                        gap: 10,
                        padding: "12px 16px",
                        borderBottom: "1px solid var(--paper-200)",
                        cursor: "pointer",
                      }}
                    >
                      <span
                        style={{
                          flexShrink: 0,
                          width: 6,
                          height: 6,
                          borderRadius: "50%",
                          marginTop: 5,
                          background: n.is_read ? "transparent" : "var(--ember-500)",
                        }}
                      />
                      <div>
                        <div style={{ fontSize: 12.5, color: "var(--ink-900)", lineHeight: 1.4, marginBottom: 3 }}>
                          {n.message}
                        </div>
                        <div style={{ fontSize: 10.5, color: "var(--ink-400)" }}>{formatNotifDate(n.created_at)}</div>
                      </div>
                    </div>
                  ))
                )}
              </div>
            )}
          </div>
        </div>

        <div
          style={{
            fontFamily: "'IBM Plex Mono', monospace",
            fontSize: 10,
            letterSpacing: "0.05em",
            color: "var(--ink-400)",
            paddingLeft: 10,
            marginBottom: 26,
            whiteSpace: "nowrap",
          }}
        >
          100%FIRE 100% WOOD
        </div>
        {links.map((link) => (
          <Link
            key={link.href}
            href={link.href}
            className={`sidebar-link ${pathname === link.href ? "active" : ""}`}
            style={{ display: "flex", alignItems: "center", gap: 10 }}
          >
            <link.Icon />
            {link.label}
          </Link>
        ))}

        <div className="sidebar-footer">
          {user && <div className="sidebar-user">{user.full_name}</div>}
          <button className="logout-btn" onClick={handleLogout}>
            Odhlásit se
          </button>
        </div>
      </aside>
      <main className="main">{children}</main>
    </div>
  );
}
