/**
 * AuthorCard — Editorial signature displayed at the bottom of every article.
 * Shows editor photo (or initials fallback), name, title, and a short tagline.
 * Includes JSON-LD structured data for Google's E-E-A-T signals.
 */

'use client';

import Image from 'next/image';

interface AuthorCardProps {
    /** Optional override — defaults to Alexander Sostin */
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


export default function AuthorCard({
    name = DEFAULT_AUTHOR.name,
    title = DEFAULT_AUTHOR.title,
    bio = DEFAULT_AUTHOR.bio,
    photoUrl = DEFAULT_AUTHOR.photoUrl,
}: AuthorCardProps) {
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
                {/* Top accent bar */}
                <div className="h-1 bg-gradient-to-r from-indigo-500 via-purple-500 to-pink-500" />

                <div className="flex items-center gap-5 p-5 sm:p-6">
                    {/* Avatar */}
                    <div className="relative shrink-0">
                        <div className="w-16 h-16 sm:w-20 sm:h-20 rounded-full overflow-hidden ring-4 ring-indigo-100 bg-indigo-50">
                            <Image
                                src={photoUrl}
                                alt={name}
                                width={80}
                                height={80}
                                className="object-cover w-full h-full"
                                onError={(e) => {
                                    // Fallback to initials if photo missing
                                    (e.target as HTMLImageElement).style.display = 'none';
                                }}
                                unoptimized
                            />
                        </div>
                        {/* Online indicator */}
                        <span className="absolute bottom-0.5 right-0.5 w-3.5 h-3.5 bg-green-400 rounded-full border-2 border-white" />
                    </div>

                    {/* Text */}
                    <div className="flex-1 min-w-0">
                        <div className="flex items-center gap-2 flex-wrap">
                            <p className="text-xs text-indigo-600 font-semibold tracking-wider uppercase">
                                Written &amp; Edited by
                            </p>
                        </div>
                        <h3 className="text-lg sm:text-xl font-black text-gray-900 leading-tight mt-0.5">
                            {name}
                        </h3>
                        <p className="text-xs sm:text-sm font-semibold text-indigo-600 mb-1.5">
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
