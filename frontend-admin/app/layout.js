import "./globals.css";

export const metadata = {
  title: "NAUHEL CRM",
  description: "Interní administrace CRM",
};

export default function RootLayout({ children }) {
  return (
    <html lang="cs">
      <head>
        <link
          href="https://fonts.googleapis.com/css2?family=IBM+Plex+Sans:wght@400;500;600;700&family=IBM+Plex+Mono:wght@400;500;600&display=swap"
          rel="stylesheet"
        />
      </head>
      <body>{children}</body>
    </html>
  );
}
