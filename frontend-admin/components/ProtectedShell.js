"use client";

import { useEffect, useState } from "react";
import { usePathname, useRouter } from "next/navigation";
import { isLoggedIn, clearToken, api } from "@/lib/api";

export default function ProtectedShell({ children }) {
  const router = useRouter();
  const pathname = usePathname();
  const [ready, setReady] = useState(false);
  const [user, setUser] = useState(null);

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
      <aside className="sidebar">
        <div className="sidebar-brand" style={{ marginBottom: 4 }}>NAUHEL CRM</div>
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
