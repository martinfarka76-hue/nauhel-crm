// Minimální service worker - jen pro splnění podmínky instalovatelnosti (Chrome/Android
// vyžaduje registrovaný fetch handler). Žádné agresivní cachování - v interním CRM
// je vždy potřeba čerstvá data, ne offline kopie.
self.addEventListener("fetch", () => {});
