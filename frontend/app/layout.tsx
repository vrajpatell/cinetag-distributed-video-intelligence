import './globals.css';
import type { Metadata } from 'next';
import { DM_Sans } from 'next/font/google';
import TopNav from '@/components/TopNav';
import FooterDebug from '@/components/FooterDebug';
import AppProviders from '@/components/providers/AppProviders';

const dmSans = DM_Sans({
  subsets: ['latin'],
  variable: '--font-dm-sans',
  display: 'swap',
});

export const metadata: Metadata = {
  title: 'CineTag — AI-Powered Video Intelligence',
  description:
    'CineTag is a cloud-native video intelligence platform that processes video assets at scale, generates LLM-powered metadata, and powers semantic discovery and recommendation-ready experiences for streaming platforms.',
  icons: { icon: '/favicon.svg' },
  openGraph: {
    title: 'CineTag — AI-Powered Video Intelligence',
    description:
      'Distributed video processing, LLM tagging, and recommendation-ready discovery for streaming platforms.',
    type: 'website',
  },
};

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="en" className={`dark ${dmSans.variable}`}>
      <body className="min-h-screen flex flex-col font-sans antialiased">
        <AppProviders>
          <TopNav />
          <main className="flex-1">{children}</main>
          <FooterDebug />
        </AppProviders>
      </body>
    </html>
  );
}
