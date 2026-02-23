'use client';

import Header from '@/components/public/Header';
import Footer from '@/components/public/Footer';
import StickyBottomAd from '@/components/public/StickyBottomAd';
import ABSeedProvider from '@/components/public/ABSeedProvider';
import ThemeContextProvider from '@/components/public/ThemeProvider';

export default function PublicLayout({
    children,
}: {
    children: React.ReactNode;
}) {
    return (
        <ThemeContextProvider>
            <ABSeedProvider />
            <Header />
            {children}
            <Footer />
            <StickyBottomAd />
        </ThemeContextProvider>
    );
}

