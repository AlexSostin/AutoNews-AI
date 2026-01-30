import type { Metadata } from "next";
import Script from 'next/script';
import ErrorBoundary from "@/components/public/ErrorBoundary";
import "./globals.css";
import BackToTop from "@/components/public/BackToTop";
import CookieConsent from "@/components/public/CookieConsent";
import { Toaster } from 'react-hot-toast';

async function getGAId() {
  const PRODUCTION_API_URL = 'https://heroic-healing-production-2365.up.railway.app/api/v1';
  const apiUrl = process.env.NEXT_PUBLIC_API_URL || PRODUCTION_API_URL;

  try {
    const res = await fetch(`${apiUrl}/settings/`, { next: { revalidate: 3600 } });
    if (res.ok) {
      const data = await res.json();
      return data.google_analytics_id;
    }
  } catch (e) {
    // Silent error in layout
  }
  return null;
}

export const metadata: Metadata = {
  title: "Fresh Motors - Latest Automotive News & Reviews",
  description: "Your source for the latest automotive news, car reviews, and industry insights.",
};

export default async function RootLayout({
  children,
}: Readonly<{
  children: React.ReactNode;
}>) {
  const gaId = await getGAId();

  return (
    <html lang="en">
      <head>
        {gaId && (
          <>
            <Script
              src={`https://www.googletagmanager.com/gtag/js?id=${gaId}`}
              strategy="afterInteractive"
            />
            <Script id="google-analytics" strategy="afterInteractive">
              {`
                window.dataLayer = window.dataLayer || [];
                function gtag(){dataLayer.push(arguments);}
                gtag('js', new Date());
                gtag('config', '${gaId}');
              `}
            </Script>
          </>
        )}
        <Script
          async
          src="https://pagead2.googlesyndication.com/pagead/js/adsbygoogle.js?client=ca-pub-1075473812019633"
          crossOrigin="anonymous"
          strategy="afterInteractive"
        />
        {/* Restore auth cookies from localStorage before page load */}
        <script
          dangerouslySetInnerHTML={{
            __html: `
              (function() {
                try {
                  var accessToken = localStorage.getItem('access_token');
                  var refreshToken = localStorage.getItem('refresh_token');
                  var isSecure = location.protocol === 'https:';
                  var secureFlag = isSecure ? '; Secure' : '';
                  var maxAge = 7 * 24 * 60 * 60;
                  
                  if (accessToken && !document.cookie.includes('access_token=')) {
                    document.cookie = 'access_token=' + accessToken + '; path=/; max-age=' + maxAge + '; SameSite=Lax' + secureFlag;
                  }
                  if (refreshToken && !document.cookie.includes('refresh_token=')) {
                    document.cookie = 'refresh_token=' + refreshToken + '; path=/; max-age=' + maxAge + '; SameSite=Lax' + secureFlag;
                  }
                } catch(e) {}
              })();
            `,
          }}
        />
      </head>
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
        <ErrorBoundary>
          {children}
        </ErrorBoundary>
        <BackToTop />
        <CookieConsent />
      </body>
    </html>
  );
}
