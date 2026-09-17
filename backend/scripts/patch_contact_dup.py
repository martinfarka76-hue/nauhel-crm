import re

path = "app/companies/[id]/page.js"
with open(path) as f:
    content = f.read()

patches = [
    (
        '  const [editingContactId, setEditingContactId] = useState(null);\n  const [editContactForm, setEditContactForm] = useState(emptyContactForm);\n\n  function loadAll() {',
        '  const [editingContactId, setEditingContactId] = useState(null);\n  const [editContactForm, setEditContactForm] = useState(emptyContactForm);\n  const [contactDupMatches, setContactDupMatches] = useState([]);\n\n  function loadAll() {'
    ),
    (
        '  useEffect(loadAll, [id]);\n\n  function handleCopyLink(accessToken, docId) {',
        '''  useEffect(loadAll, [id]);

  useEffect(() => {
    if (!showContactForm || !newContactForm.email.trim()) {
      setContactDupMatches([]);
      return;
    }
    const timer = setTimeout(() => {
      const params = new URLSearchParams({ email: newContactForm.email.trim() });
      api
        .get(`/contacts/check-duplicate?${params.toString()}`)
        .then((matches) => setContactDupMatches(matches))
        .catch(() => setContactDupMatches([]));
    }, 400);
    return () => clearTimeout(timer);
  }, [newContactForm.email, showContactForm]);

  function handleCopyLink(accessToken, docId) {'''
    ),
    (
        '      await api.post("/contacts", { company_id: id, ...newContactForm });\n      setNewContactForm(emptyContactForm);\n      setShowContactForm(false);\n      loadAll();',
        '      await api.post("/contacts", { company_id: id, ...newContactForm });\n      setNewContactForm(emptyContactForm);\n      setContactDupMatches([]);\n      setShowContactForm(false);\n      loadAll();'
    ),
    (
        '''              <div className="field" style={{ marginBottom: 8 }}>
                <label>Email</label>
                <input
                  type="email"
                  value={newContactForm.email}
                  onChange={(e) => setNewContactForm({ ...newContactForm, email: e.target.value })}
                />
              </div>
              <div className="field" style={{ marginBottom: 8 }}>
                <label>Telefon</label>''',
        '''              <div className="field" style={{ marginBottom: 8 }}>
                <label>Email</label>
                <input
                  type="email"
                  value={newContactForm.email}
                  onChange={(e) => setNewContactForm({ ...newContactForm, email: e.target.value })}
                />
              </div>
              {contactDupMatches.length > 0 && (
                <div
                  style={{
                    background: "#fdf3ec",
                    border: "1px solid var(--ember-500)",
                    borderRadius: 8,
                    padding: "8px 10px",
                    marginBottom: 8,
                    fontSize: 12,
                  }}
                >
                  <strong>⚠️ Možná duplicita</strong> - kontakt s tímto e-mailem už existuje:
                  <ul style={{ margin: "4px 0 0", paddingLeft: 16 }}>
                    {contactDupMatches.map((m) => (
                      <li key={m.id}>
                        {m.first_name} {m.last_name}
                      </li>
                    ))}
                  </ul>
                </div>
              )}
              <div className="field" style={{ marginBottom: 8 }}>
                <label>Telefon</label>'''
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
