"use client";

import { useEffect, useState, useRef } from "react";
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
    { href: "/", label: "Přehled" },
    { href: "/companies", label: "Firmy" },
    { href: "/contacts", label: "Kontakty" },
    { href: "/documents", label: "Dokumenty" },
    { href: "/settings", label: "Nastavení" },
  ];

  return (
    <div className="app-shell">
      <aside className="sidebar" style={{ position: "relative" }}>
        <div style={{ display: "flex", alignItems: "flex-start", justifyContent: "space-between", marginBottom: 4 }}>
          <div className="sidebar-brand" style={{ marginBottom: 0 }}>NAUHEL CRM</div>

          <div ref={panelRef} style={{ position: "relative" }}>
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
          <a
            key={link.href}
            href={link.href}
            className={`sidebar-link ${pathname === link.href ? "active" : ""}`}
          >
            {link.label}
          </a>
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
