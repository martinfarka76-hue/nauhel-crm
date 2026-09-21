path = "components/ProtectedShell.js"
with open(path) as f:
    content = f.read()

patches = [
    (
        'export default function ProtectedShell({ children }) {\n  const router = useRouter();\n  const pathname = usePathname();\n  const [ready, setReady] = useState(false);\n  const [user, setUser] = useState(null);',
        'export default function ProtectedShell({ children }) {\n  const router = useRouter();\n  const pathname = usePathname();\n  const [ready, setReady] = useState(false);\n  const [user, setUser] = useState(null);\n  const [mobileMenuOpen, setMobileMenuOpen] = useState(false);'
    ),
    (
        'function BellIcon() {',
        '''function MenuIcon() {
  return (
    <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.8" strokeLinecap="round" strokeLinejoin="round">
      <line x1="4" y1="7" x2="20" y2="7" />
      <line x1="4" y1="12" x2="20" y2="12" />
      <line x1="4" y1="17" x2="20" y2="17" />
    </svg>
  );
}

function CloseIcon() {
  return (
    <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.8" strokeLinecap="round" strokeLinejoin="round">
      <line x1="18" y1="6" x2="6" y2="18" />
      <line x1="6" y1="6" x2="18" y2="18" />
    </svg>
  );
}

function BellIcon() {'''
    ),
    (
        '  return (\n    <div className="app-shell">\n      <aside className="sidebar" style={{ position: "relative" }}>',
        '''  return (
    <div className="app-shell">
      <div className="mobile-topbar">
        <NauhelLogo height={14} />
        <button className="mobile-menu-btn" onClick={() => setMobileMenuOpen(!mobileMenuOpen)} aria-label="Menu">
          {mobileMenuOpen ? <CloseIcon /> : <MenuIcon />}
        </button>
      </div>
      <aside className={`sidebar ${mobileMenuOpen ? "mobile-open" : ""}`} style={{ position: "relative" }}>'''
    ),
    (
        '''        {links.map((link) => (
          <Link
            key={link.href}
            href={link.href}
            className={`sidebar-link ${pathname === link.href ? "active" : ""}`}
            style={{ display: "flex", alignItems: "center", gap: 10 }}
          >
            <link.Icon />
            {link.label}
          </Link>
        ))}''',
        '''        {links.map((link) => (
          <Link
            key={link.href}
            href={link.href}
            onClick={() => setMobileMenuOpen(false)}
            className={`sidebar-link ${pathname === link.href ? "active" : ""}`}
            style={{ display: "flex", alignItems: "center", gap: 10 }}
          >
            <link.Icon />
            {link.label}
          </Link>
        ))}'''
    ),
]

ok = True
for i, (old, new) in enumerate(patches):
    count = content.count(old)
    if count != 1:
        print(f"CHYBA patch {i+1}: nalezeno {count}x (ocekavano 1x)")
        ok = False
    else:
        content = content.replace(old, new)

if ok:
    with open(path, 'w') as f:
        f.write(content)
    print("Vsechny 4 patche zapsany uspesne")
else:
    print("NIC nebylo zapsano kvuli chybe vyse")
