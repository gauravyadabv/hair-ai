import type { Metadata } from 'next'
import './globals.css'

export const metadata: Metadata = {
  title: 'Hair Health AI — Intelligence Engine',
  description: 'Evidence-based hair health screening and photo quality analysis',
}

export default function RootLayout({
  children,
}: {
  children: React.ReactNode
}) {
  return (
    <html lang="en">
      <body>{children}</body>
    </html>
  )
}

