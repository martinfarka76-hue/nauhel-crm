export const metadata = {
  title: "NAUHEL CRM — Admin",
  description: "Interní administrace CRM",
};

export default function RootLayout({ children }) {
  return (
    <html lang="cs">
      <body>{children}</body>
    </html>
  );
}
