import type { Metadata } from "next";
import "./globals.css";
import BackToTop from "@/components/public/BackToTop";
import CookieConsent from "@/components/public/CookieConsent";
import { Toaster } from 'react-hot-toast';

export const metadata: Metadata = {
  title: "AutoNews - Latest Automotive News & Reviews",
  description: "Your source for the latest automotive news, car reviews, and industry insights.",
};

export default function RootLayout({
  children,
}: Readonly<{
  children: React.ReactNode;
}>) {
  return (
    <html lang="en">
      <body className="antialiased min-h-screen flex flex-col bg-gray-50">
        <Toaster 
          position="top-center"
          reverseOrder={false}
          toastOptions={{
            duration: 3000,
            style: {
              borderRadius: '12px',
              fontSize: '16px',
            },
            success: {
              iconTheme: {
                primary: '#10B981',
                secondary: '#fff',
              },
            },
            error: {
              iconTheme: {
                primary: '#EF4444',
                secondary: '#fff',
              },
            },
          }}
        />
        {children}
        <BackToTop />
        <CookieConsent />
      </body>
    </html>
  );
}
