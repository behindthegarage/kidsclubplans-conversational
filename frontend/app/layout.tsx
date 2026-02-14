import type { Metadata } from 'next';
import './globals.css';

export const metadata: Metadata = {
  title: 'KidsClubPlans - AI Activity Planning',
  description: 'AI-powered conversational interface for planning kids activities',
};

export default function RootLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  return (
    <html lang="en" suppressHydrationWarning>
      <body className="min-h-screen bg-background font-sans antialiased">
        {children}
      </body>
    </html>
  );
}
