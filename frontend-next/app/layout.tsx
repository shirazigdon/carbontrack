import type { Metadata } from 'next';
import './globals.css';

export const metadata: Metadata = {
  title: 'CarbonTrack360 — נתיבי ישראל',
  description: 'מערכת ניהול פליטות פחמן',
  icons: { icon: 'https://storage.googleapis.com/green_excal/carbontrack-logo.png' },
};

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="he" dir="rtl">
      <body>{children}</body>
    </html>
  );
}
