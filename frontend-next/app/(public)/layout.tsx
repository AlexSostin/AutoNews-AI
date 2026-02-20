'use client';

import Header from '@/components/public/Header';
import Footer from '@/components/public/Footer';
import StickyBottomAd from '@/components/public/StickyBottomAd';
import ABSeedProvider from '@/components/public/ABSeedProvider';

export default function PublicLayout({
    children,
}: {
    children: React.ReactNode;
}) {
    return (
        <>
            <ABSeedProvider />
            <Header />
            {children}
            <Footer />
            <StickyBottomAd />
        </>
    );
}
