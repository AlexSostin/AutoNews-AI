'use client';

/**
 * SourceAttribution — displays a "thank you" or "source" block at the bottom
 * of an article, depending on whether the originating channel is a partner.
 *
 * Partner channels (is_partner = true):
 *   🎬 Special thanks to our friends at [AutoTopNL ↗]
 *
 * Regular sources (is_partner = false):
 *   📰 Source: [Kia Worldwide]
 */

import { Youtube, Rss, ExternalLink } from 'lucide-react';

interface SourceAttributionProps {
    /** Display name of the channel / feed */
    channelName: string | null | undefined;
    /** Link to the channel or feed website */
    channelUrl: string | null | undefined;
    /** True = partner (explicit permission granted) */
    isPartner: boolean;
    /** 'youtube' | 'rss' — determines icon */
    sourceType?: 'youtube' | 'rss';
}

/** Renders channel name as a link (if URL present) or plain text. */
function ChannelLink({ name, url, className, weight = 'font-bold' }: {
    name: string;
    url: string | null | undefined;
    className: string;
    weight?: string;
}) {
    if (url) {
        return (
            <a
                href={url}
                target="_blank"
                rel="noopener noreferrer"
                className={`${weight} inline-flex items-center gap-1 transition-colors ${className}`}
            >
                {name}
                <ExternalLink size={13} className="inline" />
            </a>
        );
    }
    return <span className={`${weight} ${className}`}>{name}</span>;
}

export default function SourceAttribution({
    channelName,
    channelUrl,
    isPartner,
    sourceType = 'youtube',
}: SourceAttributionProps) {
    if (!channelName) return null;

    const Icon = sourceType === 'rss' ? Rss : Youtube;
    const iconColor = sourceType === 'rss' ? 'text-orange-500' : 'text-red-500';
    const accentColor = isPartner ? 'text-indigo-600 hover:text-indigo-800' : 'text-gray-600 hover:text-gray-900';
    const borderColor = isPartner ? 'border-indigo-100' : 'border-gray-100';
    const bgColor = isPartner ? 'bg-indigo-50/50' : 'bg-gray-50/60';

    const label = isPartner ? (
        <>
            Special thanks to our friends at{' '}
            <ChannelLink name={channelName} url={channelUrl} className={accentColor} />
        </>
    ) : (
        <>
            Source:{' '}
            <ChannelLink name={channelName} url={channelUrl} className={accentColor} weight="font-semibold" />
        </>
    );

    return (
        <div
            className={`flex items-center gap-3 px-5 py-3.5 rounded-xl border ${borderColor} ${bgColor} text-sm text-gray-700`}
        >
            <Icon size={18} className={`shrink-0 ${iconColor}`} />
            <span className={isPartner ? 'text-indigo-800' : ''}>{label}</span>
        </div>
    );
}
