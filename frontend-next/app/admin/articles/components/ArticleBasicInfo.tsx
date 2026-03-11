import React from 'react';
import { FormCard, FormField } from '@/app/admin/components/forms/FormCard';
import { Type, Search } from 'lucide-react';

interface ArticleBasicInfoProps {
    title: string;
    slug: string;
    summary: string;
    seoDescription: string;
    onTitleChange: (v: string) => void;
    onSlugChange: (v: string) => void;
    onSummaryChange: (v: string) => void;
    onSeoDescriptionChange: (v: string) => void;
}

export function ArticleBasicInfo({
    title,
    slug,
    summary,
    seoDescription,
    onTitleChange,
    onSlugChange,
    onSummaryChange,
    onSeoDescriptionChange
}: ArticleBasicInfoProps) {
    const seoCharCount = seoDescription.length;
    const seoIsOver = seoCharCount > 160;
    const seoIsGood = seoCharCount >= 120 && seoCharCount <= 160;

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

                <FormField label="Summary" htmlFor="summary" required description="Visible description shown on article cards and lists.">
                    <textarea
                        id="summary"
                        value={summary}
                        onChange={(e) => onSummaryChange(e.target.value)}
                        rows={3}
                        className="w-full px-4 py-3 bg-gray-50 border border-gray-200 rounded-xl focus:ring-2 focus:ring-indigo-500 focus:border-indigo-500 transition-all resize-y text-gray-900"
                        placeholder="A brief, engaging overview of the article..."
                        required
                    />
                </FormField>

                <FormField
                    label={
                        <span className="flex items-center gap-2">
                            <Search size={14} className="text-green-600" />
                            SEO Description
                        </span>
                    }
                    htmlFor="seo_description"
                    description="For Google search results. Aim for 120-160 characters."
                >
                    <textarea
                        id="seo_description"
                        value={seoDescription}
                        onChange={(e) => {
                            if (e.target.value.length <= 165) {
                                onSeoDescriptionChange(e.target.value);
                            }
                        }}
                        rows={2}
                        className={`w-full px-4 py-3 bg-gray-50 border rounded-xl focus:ring-2 focus:ring-indigo-500 focus:border-indigo-500 transition-all resize-none text-gray-900 ${
                            seoIsOver ? 'border-red-300 bg-red-50' : 'border-gray-200'
                        }`}
                        placeholder="Keyword-rich description for Google (max 160 chars)..."
                    />
                    <div className="flex items-center justify-between mt-1.5">
                        <span className="text-xs text-gray-400">
                            Used in &lt;meta&gt; description tag for search engines
                        </span>
                        <span className={`text-xs font-mono font-bold ${
                            seoIsOver ? 'text-red-500' :
                            seoIsGood ? 'text-green-600' :
                            'text-yellow-600'
                        }`}>
                            {seoCharCount}/160
                        </span>
                    </div>
                </FormField>
            </div>
        </FormCard>
    );
}
