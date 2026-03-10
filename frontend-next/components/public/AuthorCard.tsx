/**
 * AuthorCard — Editorial signature displayed at the bottom of every article.
 * Shows editor photo, name, title, and a short tagline.
 * Accent colours match the active site theme (Indigo / Emerald / Ocean Blue).
 * Includes JSON-LD structured data for Google's E-E-A-T signals.
 */

'use client';

import Image from 'next/image';
import { useTheme } from '@/components/public/ThemeProvider';

interface AuthorCardProps {
    name?: string;
    title?: string;
    bio?: string;
    photoUrl?: string;
}

const DEFAULT_AUTHOR = {
    name: 'Alexander Sostin',
    title: 'CEO & Editor-in-Chief',
    bio: 'Automotive journalist and entrepreneur. Covering the global EV market, emerging Chinese brands, and the future of mobility.',
    photoUrl: '/alex-sostin.jpg',
};

/** Map theme id → Tailwind gradient classes for the accent bar */
const THEME_GRADIENT: Record<string, string> = {
    '': 'from-indigo-500 via-purple-500 to-indigo-400',
    'midnight-green': 'from-emerald-500 via-teal-500 to-emerald-400',
    'deep-ocean': 'from-blue-500 via-cyan-500 to-blue-400',
};

/** Map theme id → ring + dot colour classes */
const THEME_RING: Record<string, string> = {
    '': 'ring-indigo-100',
    'midnight-green': 'ring-emerald-100',
    'deep-ocean': 'ring-blue-100',
};

const THEME_DOT: Record<string, string> = {
    '': 'bg-indigo-400',
    'midnight-green': 'bg-emerald-400',
    'deep-ocean': 'bg-blue-400',
};

const THEME_LABEL: Record<string, string> = {
    '': 'text-indigo-600',
    'midnight-green': 'text-emerald-600',
    'deep-ocean': 'text-blue-600',
};

export default function AuthorCard({
    name = DEFAULT_AUTHOR.name,
    title = DEFAULT_AUTHOR.title,
    bio = DEFAULT_AUTHOR.bio,
    photoUrl = DEFAULT_AUTHOR.photoUrl,
}: AuthorCardProps) {
    const { theme } = useTheme();

    const gradient = THEME_GRADIENT[theme] ?? THEME_GRADIENT[''];
    const ring = THEME_RING[theme] ?? THEME_RING[''];
    const dot = THEME_DOT[theme] ?? THEME_DOT[''];
    const label = THEME_LABEL[theme] ?? THEME_LABEL[''];

    const structuredData = {
        '@context': 'https://schema.org',
        '@type': 'Person',
        name,
        jobTitle: title,
        description: bio,
        image: `https://www.freshmotors.net${photoUrl}`,
        url: 'https://www.freshmotors.net',
        worksFor: {
            '@type': 'Organization',
            name: 'Fresh Motors',
            url: 'https://www.freshmotors.net',
        },
    };

    return (
        <>
            {/* JSON-LD for Google E-E-A-T */}
            <script
                type="application/ld+json"
                dangerouslySetInnerHTML={{ __html: JSON.stringify(structuredData) }}
            />

            <div className="bg-white rounded-2xl shadow-md overflow-hidden border border-gray-100">
                {/* Accent bar — matches active theme */}
                <div className={`h-1 bg-gradient-to-r ${gradient}`} />

                <div className="flex items-center gap-5 p-5 sm:p-6">
                    {/* Avatar */}
                    <div className="relative shrink-0">
                        <div className={`w-16 h-16 sm:w-20 sm:h-20 rounded-full overflow-hidden ring-4 ${ring} bg-gray-100`}>
                            <Image
                                src={photoUrl}
                                alt={name}
                                width={80}
                                height={80}
                                className="object-cover object-[center_20%] w-full h-full brightness-75"
                                unoptimized
                            />
                        </div>
                        {/* Status dot — matches active theme */}
                        <span className={`absolute bottom-0.5 right-0.5 w-3.5 h-3.5 ${dot} rounded-full border-2 border-white`} />
                    </div>

                    {/* Text */}
                    <div className="flex-1 min-w-0">
                        <p className={`text-xs ${label} font-semibold tracking-wider uppercase`}>
                            Written &amp; Edited by
                        </p>
                        <h3 className="text-lg sm:text-xl font-black text-gray-900 leading-tight mt-0.5">
                            {name}
                        </h3>
                        <p className={`text-xs sm:text-sm font-semibold ${label} mb-1.5`}>
                            {title}
                        </p>
                        <p className="text-xs sm:text-sm text-gray-500 leading-relaxed line-clamp-2">
                            {bio}
                        </p>
                    </div>
                </div>
            </div>
        </>
    );
}
