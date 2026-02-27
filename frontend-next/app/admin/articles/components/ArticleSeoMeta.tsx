import React, { ReactNode } from 'react';
import { FormCard, FormField } from '@/app/admin/components/forms/FormCard';
import { Tag as TagIcon, Youtube } from 'lucide-react';

interface ArticleSeoMetaProps {
    youtubeUrl: string;
    onYoutubeUrlChange: (v: string) => void;
    showYoutube: boolean;
    onShowYoutubeChange: (v: boolean) => void;
    categorySelector: ReactNode;
    tagSelector: ReactNode;
}

export function ArticleSeoMeta({
    youtubeUrl,
    onYoutubeUrlChange,
    showYoutube,
    onShowYoutubeChange,
    categorySelector,
    tagSelector
}: ArticleSeoMetaProps) {
    return (
        <div className="space-y-6">
            <FormCard title="Categorization & Tags" icon={<TagIcon className="text-purple-500" size={20} />}>
                <div className="space-y-6">
                    {categorySelector}

                    {tagSelector}
                </div>
            </FormCard>

            <FormCard title="Media Linking" icon={<Youtube className="text-red-500" size={20} />}>
                <div className="space-y-4">
                    <div>
                        <div className="flex items-center justify-between mb-2">
                            <label htmlFor="youtubeUrl" className="block text-sm font-medium text-gray-700">YouTube URL</label>
                            <button
                                type="button"
                                onClick={() => onShowYoutubeChange(!showYoutube)}
                                className={`flex items-center gap-1.5 px-2 py-1 rounded-full text-xs font-medium transition-all ${showYoutube
                                    ? 'bg-red-100 text-red-700 hover:bg-red-200'
                                    : 'bg-gray-200 text-gray-500 hover:bg-gray-300'
                                    }`}
                                title={showYoutube ? 'YouTube embed visible on public page' : 'YouTube embed hidden from public page'}
                            >
                                {showYoutube ? 'Visible' : 'Hidden'}
                            </button>
                        </div>
                        <input
                            id="youtubeUrl"
                            type="url"
                            value={youtubeUrl}
                            onChange={(e) => onYoutubeUrlChange(e.target.value)}
                            className={`w-full px-4 py-3 bg-gray-50 border border-gray-200 rounded-xl focus:ring-2 focus:ring-red-500 focus:border-red-500 transition-all text-gray-900 ${!showYoutube ? 'opacity-50' : ''}`}
                            placeholder="https://youtube.com/watch?v=..."
                        />
                    </div>
                </div>
            </FormCard>
        </div>
    );
}
