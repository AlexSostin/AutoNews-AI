import type { Metadata } from "next";
import "./globals.css";
import BackToTop from "@/components/public/BackToTop";
import CookieConsent from "@/components/public/CookieConsent";
import { Toaster } from 'react-hot-toast';

export const metadata: Metadata = {
  title: "Fresh Motors - Latest Automotive News & Reviews",
  description: "Your source for the latest automotive news, car reviews, and industry insights.",
};

export default function RootLayout({
  children,
}: Readonly<{
  children: React.ReactNode;
}>) {
  return (
    <html lang="en">
      <head>
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
        {children}
        <BackToTop />
        <CookieConsent />
      </body>
    </html>
  );
}
