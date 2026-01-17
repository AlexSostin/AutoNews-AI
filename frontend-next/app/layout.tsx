import type { Metadata } from "next";
import "./globals.css";
import BackToTop from "@/components/public/BackToTop";

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
        {children}
        <BackToTop />
      </body>
    </html>
  );
}
