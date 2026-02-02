'use client';

import { useEffect } from 'react';

export default function AdSenseScript() {
    useEffect(() => {
        // Only run on client
        if (typeof window === 'undefined') return;

        // Check if script already exists
        if (document.querySelector('script[src*="adsbygoogle.js"]')) return;

        try {
            const script = document.createElement('script');
            script.src = "https://pagead2.googlesyndication.com/pagead/js/adsbygoogle.js?client=ca-pub-1075473812019633";
            script.async = true;
            script.crossOrigin = "anonymous";

            // Inject into head
            document.head.appendChild(script);

            console.log('✅ AdSense script injected manually to avoid data-nscript warning');
        } catch (error) {
            console.error('❌ Failed to inject AdSense script:', error);
        }
    }, []);

    return null;
}
