import React from 'react';
import { FormCard, FormField } from '@/app/admin/components/forms/FormCard';
import { Type } from 'lucide-react';

interface ArticleBasicInfoProps {
    title: string;
    slug: string;
    summary: string;
    onTitleChange: (v: string) => void;
    onSlugChange: (v: string) => void;
    onSummaryChange: (v: string) => void;
}

export function ArticleBasicInfo({
    title,
    slug,
    summary,
    onTitleChange,
    onSlugChange,
    onSummaryChange
}: ArticleBasicInfoProps) {
    return (
        <FormCard title="Basic Information" icon={<Type className="text-indigo-500" size={20} />}>
            <div className="space-y-6">
                <FormField label="Article Title" htmlFor="title" required>
                    <input
                        id="title"
                        type="text"
                        value={title}
                        onChange={(e) => onTitleChange(e.target.value)}
                        className="w-full px-4 py-3 bg-gray-50 border border-gray-200 rounded-xl focus:ring-2 focus:ring-indigo-500 focus:border-indigo-500 transition-all text-gray-900"
                        placeholder="e.g. The Future of Electric Vehicles"
                        required
                    />
                </FormField>

                <FormField
                    label="URL Slug"
                    htmlFor="slug"
                    description="Must be unique. Leave empty to auto-generate from title."
                >
                    <div className="flex rounded-xl overflow-hidden shadow-sm border border-gray-200">
                        <span className="inline-flex items-center px-4 bg-gray-100 text-gray-500 border-r border-gray-200">
                            /articles/
                        </span>
                        <input
                            id="slug"
                            type="text"
                            value={slug}
                            onChange={(e) => onSlugChange(e.target.value.toLowerCase().replace(/[^a-z0-9-]/g, '-'))}
                            className="flex-1 px-4 py-3 bg-gray-50 focus:ring-2 focus:ring-indigo-500 focus:border-indigo-500 outline-none text-gray-900"
                            placeholder="auto-generated-slug"
                        />
                    </div>
                </FormField>

                <FormField label="Summary (SEO Description)" htmlFor="summary" required>
                    <textarea
                        id="summary"
                        value={summary}
                        onChange={(e) => onSummaryChange(e.target.value)}
                        rows={3}
                        className="w-full px-4 py-3 bg-gray-50 border border-gray-200 rounded-xl focus:ring-2 focus:ring-indigo-500 focus:border-indigo-500 transition-all resize-y text-gray-900"
                        placeholder="A brief overview of the article..."
                        required
                    />
                </FormField>
            </div>
        </FormCard>
    );
}
