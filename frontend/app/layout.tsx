import './globals.css';
import type { Metadata } from 'next';
import TopNav from '@/components/TopNav';
import FooterDebug from '@/components/FooterDebug';

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
    <html lang="en" className="dark">
      <body className="min-h-screen flex flex-col">
        <TopNav />
        <main className="flex-1">{children}</main>
        <FooterDebug />
      </body>
    </html>
  );
}
