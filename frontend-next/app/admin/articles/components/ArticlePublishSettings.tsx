import React from 'react';
import { FormCard } from '@/app/admin/components/forms/FormCard';
import { Settings, Eye, Star, Newspaper, Clock } from 'lucide-react';

interface ArticlePublishSettingsProps {
    isPublished: boolean;
    isHero: boolean;
    isNewsOnly: boolean;
    scheduledPublishAt: string;
    onPublishedChange: (v: boolean) => void;
    onHeroChange: (v: boolean) => void;
    onNewsOnlyChange: (v: boolean) => void;
    onScheduledPublishAtChange: (v: string) => void;
}

export function ArticlePublishSettings({
    isPublished,
    isHero,
    isNewsOnly,
    scheduledPublishAt,
    onPublishedChange,
    onHeroChange,
    onNewsOnlyChange,
    onScheduledPublishAtChange,
}: ArticlePublishSettingsProps) {
    const hasSchedule = !!scheduledPublishAt;

    // Quick schedule presets (in hours from now)
    const presets = [
        { label: '1h', hours: 1 },
        { label: '2h', hours: 2 },
        { label: '4h', hours: 4 },
        { label: '8h', hours: 8 },
        { label: '24h', hours: 24 },
    ];

    const setPreset = (hours: number) => {
        const d = new Date(Date.now() + hours * 3600_000);
        // Format as local datetime-local value
        const local = new Date(d.getTime() - d.getTimezoneOffset() * 60_000)
            .toISOString()
            .slice(0, 16);
        onScheduledPublishAtChange(local);
    };

    return (
        <div className="space-y-6">
            <FormCard title="Publish Settings" icon={<Settings className="text-gray-500" size={20} />}>
                <div className="space-y-4">
                    <label className="flex items-center justify-between p-4 bg-gray-50 border border-gray-200 rounded-xl cursor-pointer hover:bg-gray-100 transition-colors">
                        <div className="flex items-center gap-3">
                            <Eye className={isPublished ? 'text-green-500' : 'text-gray-400'} size={20} />
                            <div>
                                <span className="block font-medium text-gray-900">Published</span>
                                <span className="text-sm text-gray-500">Visible to public</span>
                            </div>
                        </div>
                        <div className={`relative inline-flex h-6 w-11 items-center rounded-full transition-colors ${isPublished ? 'bg-green-500' : 'bg-gray-300'}`}>
                            <span className={`inline-block h-4 w-4 transform rounded-full bg-white transition-transform ${isPublished ? 'translate-x-6' : 'translate-x-1'}`} />
                            <input
                                type="checkbox"
                                className="sr-only"
                                checked={isPublished}
                                onChange={(e) => {
                                    onPublishedChange(e.target.checked);
                                    // If publishing now, clear scheduled time
                                    if (e.target.checked && scheduledPublishAt) {
                                        onScheduledPublishAtChange('');
                                    }
                                }}
                            />
                        </div>
                    </label>

                    {/* Scheduled Publish */}
                    {!isPublished && (
                        <div className={`p-4 border rounded-xl transition-all ${hasSchedule ? 'bg-indigo-50 border-indigo-200' : 'bg-gray-50 border-gray-200'}`}>
                            <div className="flex items-center gap-3 mb-3">
                                <Clock className={hasSchedule ? 'text-indigo-500' : 'text-gray-400'} size={20} />
                                <div>
                                    <span className="block font-medium text-gray-900">📅 Schedule Publish</span>
                                    <span className="text-sm text-gray-500">Auto-publish at a specific time + Telegram post</span>
                                </div>
                            </div>

                            <div className="flex items-center gap-2 mb-2">
                                <input
                                    type="datetime-local"
                                    value={scheduledPublishAt}
                                    onChange={(e) => onScheduledPublishAtChange(e.target.value)}
                                    min={new Date(Date.now() - new Date().getTimezoneOffset() * 60_000).toISOString().slice(0, 16)}
                                    className="flex-1 px-3 py-2 bg-white border border-gray-300 rounded-lg text-sm focus:ring-2 focus:ring-indigo-500 focus:border-indigo-500 text-gray-900"
                                />
                                {hasSchedule && (
                                    <button
                                        type="button"
                                        onClick={() => onScheduledPublishAtChange('')}
                                        className="px-3 py-2 text-sm font-medium text-red-600 bg-red-50 border border-red-200 rounded-lg hover:bg-red-100 transition-colors"
                                    >
                                        Clear
                                    </button>
                                )}
                            </div>

                            {/* Quick presets */}
                            <div className="flex items-center gap-1.5 flex-wrap">
                                <span className="text-xs text-gray-500 mr-1">Quick:</span>
                                {presets.map(p => (
                                    <button
                                        key={p.label}
                                        type="button"
                                        onClick={() => setPreset(p.hours)}
                                        className="px-2.5 py-1 text-xs font-medium text-indigo-600 bg-white border border-indigo-200 rounded-md hover:bg-indigo-50 transition-colors"
                                    >
                                        +{p.label}
                                    </button>
                                ))}
                            </div>

                            {hasSchedule && (
                                <div className="mt-2 flex items-center gap-2 text-sm text-indigo-700 bg-indigo-100 px-3 py-1.5 rounded-lg">
                                    <Clock size={14} />
                                    <span>
                                        Will publish at{' '}
                                        <strong>{new Date(scheduledPublishAt).toLocaleString()}</strong>
                                        {' '}+ Telegram
                                    </span>
                                </div>
                            )}
                        </div>
                    )}

                    <label className="flex items-center justify-between p-4 bg-gray-50 border border-gray-200 rounded-xl cursor-pointer hover:bg-gray-100 transition-colors">
                        <div className="flex items-center gap-3">
                            <Star className={isHero ? 'text-yellow-500' : 'text-gray-400'} size={20} />
                            <div>
                                <span className="block font-medium text-gray-900">Hero Article</span>
                                <span className="text-sm text-gray-500">Featured at top of homepage</span>
                            </div>
                        </div>
                        <div className={`relative inline-flex h-6 w-11 items-center rounded-full transition-colors ${isHero ? 'bg-yellow-500' : 'bg-gray-300'}`}>
                            <span className={`inline-block h-4 w-4 transform rounded-full bg-white transition-transform ${isHero ? 'translate-x-6' : 'translate-x-1'}`} />
                            <input
                                type="checkbox"
                                className="sr-only"
                                checked={isHero}
                                onChange={(e) => onHeroChange(e.target.checked)}
                            />
                        </div>
                    </label>

                    <label className="flex items-center justify-between p-4 bg-gray-50 border border-gray-200 rounded-xl cursor-pointer hover:bg-gray-100 transition-colors">
                        <div className="flex items-center gap-3">
                            <Newspaper className={isNewsOnly ? 'text-blue-500' : 'text-gray-400'} size={20} />
                            <div>
                                <span className="block font-medium text-gray-900">News Only</span>
                                <span className="text-sm text-gray-500">Hide from Brand Catalog pages</span>
                            </div>
                        </div>
                        <div className={`relative inline-flex h-6 w-11 items-center rounded-full transition-colors ${isNewsOnly ? 'bg-blue-500' : 'bg-gray-300'}`}>
                            <span className={`inline-block h-4 w-4 transform rounded-full bg-white transition-transform ${isNewsOnly ? 'translate-x-6' : 'translate-x-1'}`} />
                            <input
                                type="checkbox"
                                className="sr-only"
                                checked={isNewsOnly}
                                onChange={(e) => onNewsOnlyChange(e.target.checked)}
                            />
                        </div>
                    </label>
                </div>
            </FormCard>
        </div>
    );
}
