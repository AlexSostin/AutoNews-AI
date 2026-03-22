import { useState } from 'react';
import { Search, Plus, X } from 'lucide-react';
import api from '@/lib/api';

export interface Category {
    id: number;
    name: string;
    slug: string;
}

export interface Tag {
    id: number;
    name: string;
    slug: string;
    group?: number;
    group_name?: string;
}

interface TagSelectorProps<T extends { category_ids: number[]; tags: number[]; title?: string; content?: string }> {
    categories: Category[];
    tags: Tag[];
    setTags: React.Dispatch<React.SetStateAction<Tag[]>>;
    formData: T;
    setFormData: React.Dispatch<React.SetStateAction<T>>;
    handleTagToggle: (tagId: number) => void;
}

export function TagSelector<T extends { category_ids: number[]; tags: number[]; title?: string; content?: string }>({
    categories,
    tags,
    setTags,
    formData,
    setFormData,
    handleTagToggle,
}: TagSelectorProps<T>) {
    const [tagSearch, setTagSearch] = useState('');
    const [isAutoTagging, setIsAutoTagging] = useState(false);

    const handleAutoTagAI = async () => {
        if (!formData.title) {
            alert("Please provide a title to use the Smart Tagger AI.");
            return;
        }
        setIsAutoTagging(true);
        try {
            const res = await api.post('/articles/smart_tags/', {
                title: formData.title,
                content: formData.content || ''
            });
            if (res.data.tags) {
                const newTagIds = res.data.tags.map((t: Tag) => t.id);
                setFormData((prev) => ({ ...prev, tags: newTagIds }) as T);
            }
        } catch (err: any) {
            alert(`Failed to auto-tag: ${err?.response?.data?.error || err.message}`);
        } finally {
            setIsAutoTagging(false);
        }
    };

    const searchLower = tagSearch.toLowerCase();

    return (
        <>
            {/* Categories - only shown when categories are provided */}
            {categories.length > 0 && (
                <div className="mb-6">
                    <label className="block text-sm font-bold text-gray-900 mb-2">Categories *</label>
                    <div className="flex flex-wrap gap-2">
                        {categories.map((cat) => (
                            <button
                                key={cat.id}
                                type="button"
                                onClick={() => {
                                    const ids = formData.category_ids.includes(cat.id)
                                        ? formData.category_ids.filter((id: number) => id !== cat.id)
                                        : [...formData.category_ids, cat.id];
                                    setFormData((prev) => ({ ...prev, category_ids: ids }) as T);
                                }}
                                className={`px-4 py-2 rounded-lg text-sm font-bold transition-all border-2 ${formData.category_ids.includes(cat.id)
                                    ? 'bg-indigo-600 border-indigo-600 text-white shadow-md'
                                    : 'bg-white border-gray-200 text-gray-700 hover:border-indigo-300'
                                    }`}
                            >
                                {cat.name}
                                {formData.category_ids.includes(cat.id) && (
                                    <span className="ml-2">✓</span>
                                )}
                            </button>
                        ))}
                    </div>
                    {formData.category_ids.length === 0 && (
                        <p className="text-sm text-red-500 mt-1">Select at least one category</p>
                    )}
                </div>
            )}

            {/* Tags - only shown when tags are provided */}
            {tags.length > 0 && (
                <div className={categories.length > 0 ? 'border-t pt-6' : ''}>
                    <div className="flex items-center justify-between mb-2">
                        <label className="block text-lg font-bold text-gray-900">Tags</label>
                        <div className="flex items-center gap-2">
                            {formData.tags?.length > 0 && (
                                <button
                                    type="button"
                                    title="Clear all selected tags"
                                    onClick={() => {
                                        if (confirm('Clear all selected tags?')) {
                                            setFormData(prev => ({ ...prev, tags: [] }) as T);
                                        }
                                    }}
                                    className="flex items-center gap-1.5 px-3 py-1.5 bg-rose-50 hover:bg-rose-100 text-rose-600 rounded-lg text-xs font-bold transition-colors border border-rose-100 shadow-sm"
                                >
                                    🧹 Clear All
                                </button>
                            )}
                            {formData.title !== undefined && (
                                <button
                                    type="button"
                                    onClick={handleAutoTagAI}
                                    disabled={isAutoTagging}
                                    className="flex items-center gap-1.5 px-3 py-1.5 bg-indigo-50 hover:bg-indigo-100 text-indigo-700 rounded-lg text-xs font-bold transition-colors border border-indigo-100 shadow-sm disabled:opacity-50"
                                >
                                    {isAutoTagging ? (
                                        <span className="w-3 h-3 border-2 border-indigo-600 border-t-transparent rounded-full animate-spin"></span>
                                    ) : (
                                        '🏷️'
                                    )}
                                    {isAutoTagging ? 'Auto-Tagging...' : 'Smart Auto-Tag AI'}
                                </button>
                            )}
                        </div>
                    </div>
                    <p className="text-sm text-gray-600 mb-4">Select relevant tags grouped by category</p>

                    {/* Search Filter + Quick Create */}
                    <div className="relative mb-4">
                        <Search className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-gray-400" />
                        <input
                            type="text"
                            value={tagSearch}
                            onChange={(e) => setTagSearch(e.target.value)}
                            placeholder="Search or create tags..."
                            className="w-full pl-10 pr-28 py-2.5 border-2 border-gray-200 rounded-xl text-sm focus:border-indigo-400 focus:ring-2 focus:ring-indigo-100 outline-none transition-all text-gray-900 placeholder:text-gray-400"
                        />
                        <div className="absolute right-2 top-1/2 -translate-y-1/2 flex items-center gap-1">
                            {tagSearch && !tags.some(t => t.name.toLowerCase() === tagSearch.toLowerCase()) && (
                                <button
                                    type="button"
                                    onClick={async () => {
                                        const name = tagSearch.trim();
                                        if (!name) return;
                                        try {
                                            const res = await api.post('/tags/', { name });
                                            const newTag = res.data;
                                            setTags((prev: Tag[]) => [...prev, newTag]);
                                            setFormData((prev) => ({ ...prev, tags: [...(prev.tags as number[]), newTag.id] }) as T);
                                            setTagSearch('');
                                        } catch (err: unknown) {
                                            const e = err as { response?: { data?: { name?: string[] } }; message?: string };
                                            alert(`Failed to create tag: ${e.response?.data?.name?.[0] || e.message}`);
                                        }
                                    }}
                                    className="flex items-center gap-1 px-2.5 py-1 bg-emerald-500 text-white rounded-lg text-xs font-bold hover:bg-emerald-600 transition-colors whitespace-nowrap"
                                >
                                    <Plus className="w-3 h-3" />
                                    Create &quot;{tagSearch.length > 15 ? tagSearch.slice(0, 15) + '…' : tagSearch}&quot;
                                </button>
                            )}
                            {tagSearch && (
                                <button
                                    type="button"
                                    onClick={() => setTagSearch('')}
                                    className="text-gray-400 hover:text-gray-600 p-1"
                                >
                                    <X className="w-4 h-4" />
                                </button>
                            )}
                        </div>
                    </div>

                    {/* Selected tags summary */}
                    {formData.tags.length > 0 && (
                        <div className="mb-4 flex flex-wrap gap-1.5">
                            {tags.filter(t => formData.tags.includes(t.id)).map(tag => (
                                <span
                                    key={tag.id}
                                    className="inline-flex items-center gap-1 px-2.5 py-1 bg-indigo-100 text-indigo-800 rounded-full text-xs font-semibold"
                                >
                                    {tag.name}
                                    <button
                                        type="button"
                                        onClick={() => handleTagToggle(tag.id)}
                                        className="hover:text-indigo-950"
                                    >
                                        <X className="w-3 h-3" />
                                    </button>
                                </span>
                            ))}
                        </div>
                    )}

                    {/* Search results dropdown */}
                    {tagSearch && (
                        <div className="mb-4 bg-white border border-gray-200 rounded-xl shadow-lg p-3 flex flex-wrap gap-2 max-h-64 overflow-y-auto">
                            {tags
                                .filter(t => !formData.tags.includes(t.id) && t.name.toLowerCase().includes(searchLower))
                                .slice(0, 30)
                                .map(tag => (
                                    <button
                                        key={tag.id}
                                        type="button"
                                        onClick={() => {
                                            handleTagToggle(tag.id);
                                            setTagSearch('');
                                        }}
                                        className="px-3 py-1.5 bg-gray-50 border border-gray-200 text-gray-700 rounded-lg text-sm font-semibold hover:bg-indigo-50 hover:text-indigo-600 hover:border-indigo-300 transition-colors flex items-center"
                                    >
                                        <span className="text-xs text-gray-400 mr-2 font-normal">{tag.group_name || 'General'}</span>
                                        {tag.name}
                                    </button>
                                ))}
                            {tags.filter(t => t.name.toLowerCase().includes(searchLower)).length === 0 && (
                                <p className="text-sm text-gray-500 py-2 px-2">No matching tags found. You can click Create to add it.</p>
                            )}
                        </div>
                    )}
                </div>
            )}
        </>
    );
}
