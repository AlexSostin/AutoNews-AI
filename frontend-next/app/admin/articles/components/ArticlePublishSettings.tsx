import React from 'react';
import { FormCard } from '@/app/admin/components/forms/FormCard';
import { Settings, Eye, Star } from 'lucide-react';

interface ArticlePublishSettingsProps {
    isPublished: boolean;
    isHero: boolean;
    onPublishedChange: (v: boolean) => void;
    onHeroChange: (v: boolean) => void;
}

export function ArticlePublishSettings({
    isPublished,
    isHero,
    onPublishedChange,
    onHeroChange,
}: ArticlePublishSettingsProps) {
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
                                onChange={(e) => onPublishedChange(e.target.checked)}
                            />
                        </div>
                    </label>

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
                </div>
            </FormCard>
        </div>
    );
}
