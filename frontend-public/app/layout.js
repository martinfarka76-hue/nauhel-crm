export const metadata = {
  title: "NAUHEL CRM — Nabídka",
  description: "Veřejné zobrazení nabídky",
};

export default function RootLayout({ children }) {
  return (
    <html lang="cs">
      <body>{children}</body>
    </html>
  );
}
