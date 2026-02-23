'use client';

import ABSeedProvider from '@/components/public/ABSeedProvider';
import ThemeProvider from '@/components/public/ThemeProvider';

export default function AuthLayout({
    children,
}: {
    children: React.ReactNode;
}) {
    return (
        <>
            <ABSeedProvider />
            <ThemeProvider>
                {children}
            </ThemeProvider>
        </>
    );
}
