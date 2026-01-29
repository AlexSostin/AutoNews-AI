'use client';

import Header from '@/components/public/Header';
import Footer from '@/components/public/Footer';
import StickyBottomAd from '@/components/public/StickyBottomAd';

export default function PublicLayout({
    children,
}: {
    children: React.ReactNode;
}) {
    return (
        <>
            <Header />
            {children}
            <Footer />
            <StickyBottomAd />
        </>
    );
}
