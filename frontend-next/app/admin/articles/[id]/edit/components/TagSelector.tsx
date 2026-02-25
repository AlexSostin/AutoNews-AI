import { useState } from 'react';
import { Search, Plus, X, ChevronDown } from 'lucide-react';
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

interface TagSelectorProps {
    categories: Category[];
    tags: Tag[];
    setTags: React.Dispatch<React.SetStateAction<Tag[]>>;
    formData: {
        category_ids: number[];
        tags: number[];
        [key: string]: any;
    };
    setFormData: React.Dispatch<React.SetStateAction<any>>;
    handleTagToggle: (tagId: number) => void;
}

export function TagSelector({
    categories,
    tags,
    setTags,
    formData,
    setFormData,
    handleTagToggle
}: TagSelectorProps) {
    const [tagSearch, setTagSearch] = useState('');
    const [collapsedGroups, setCollapsedGroups] = useState<Set<string>>(new Set());
    const [letterFilter, setLetterFilter] = useState<Record<string, string | null>>({});
    const [addingTagGroup, setAddingTagGroup] = useState<string | null>(null);
    const [newTagName, setNewTagName] = useState('');

    const LETTER_COLORS: Record<string, string> = {
        A: 'bg-blue-500', B: 'bg-emerald-500', C: 'bg-violet-500', D: 'bg-amber-500',
        E: 'bg-rose-500', F: 'bg-cyan-500', G: 'bg-indigo-500', H: 'bg-orange-500',
        I: 'bg-teal-500', J: 'bg-pink-500', K: 'bg-lime-600', L: 'bg-purple-500',
        M: 'bg-sky-500', N: 'bg-red-500', O: 'bg-green-500', P: 'bg-fuchsia-500',
        Q: 'bg-yellow-600', R: 'bg-blue-600', S: 'bg-emerald-600', T: 'bg-violet-600',
        U: 'bg-amber-600', V: 'bg-rose-600', W: 'bg-cyan-600', X: 'bg-indigo-600',
        Y: 'bg-orange-600', Z: 'bg-teal-600',
    };
    const getLetterColor = (letter: string) => LETTER_COLORS[letter.toUpperCase()] || 'bg-gray-500';
    const ALPHA_GROUPED = ['Manufacturers', 'Models'];

    const searchLower = tagSearch.toLowerCase();
    const grouped = tags.reduce((acc, tag) => {
        const group = tag.group_name || 'General';
        if (!acc[group]) acc[group] = [];
        acc[group].push(tag);
        return acc;
    }, {} as Record<string, Tag[]>);

    const renderTagButton = (tag: Tag) => (
        <button
            key={tag.id}
            type="button"
            onClick={() => handleTagToggle(tag.id)}
            className={`px-3 py-1.5 rounded-lg text-sm font-semibold transition-all border-2 ${formData.tags.includes(tag.id)
                ? 'bg-indigo-600 border-indigo-600 text-white shadow-md scale-105'
                : 'bg-white border-gray-200 text-gray-700 hover:border-indigo-300 hover:text-indigo-600 hover:bg-indigo-50/50'
                }`}
        >
            {tag.name}
            {formData.tags.includes(tag.id) && (
                <span className="ml-1.5 inline-flex items-center justify-center w-4 h-4 bg-white/20 rounded-full text-[10px]">✓</span>
            )}
        </button>
    );

    return (
        <>
            {/* Categories */}
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
                                setFormData({ ...formData, category_ids: ids });
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

            {/* Tags */}
            <div className="border-t pt-6">
                <label className="block text-lg font-bold text-gray-900 mb-2">Tags & Categories</label>
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
                                        setFormData((prev: any) => ({ ...prev, tags: [...prev.tags, newTag.id] }));
                                        setTagSearch('');
                                    } catch (err: any) {
                                        alert(`Failed to create tag: ${err.response?.data?.name?.[0] || err.message}`);
                                    }
                                }}
                                className="flex items-center gap-1 px-2.5 py-1 bg-emerald-500 text-white rounded-lg text-xs font-bold hover:bg-emerald-600 transition-colors whitespace-nowrap"
                            >
                                <Plus className="w-3 h-3" />
                                Create "{tagSearch.length > 15 ? tagSearch.slice(0, 15) + '…' : tagSearch}"
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

                <div className="space-y-2">
                    {Object.entries(grouped)
                        .sort(([a], [b]) => {
                            if (a === 'General') return 1;
                            if (b === 'General') return -1;
                            return a.localeCompare(b);
                        })
                        .map(([groupName, groupTags]) => {
                            const filteredTags = tagSearch
                                ? groupTags.filter(t => t.name.toLowerCase().includes(searchLower))
                                : groupTags;

                            if (tagSearch && filteredTags.length === 0) return null;

                            const selectedCount = groupTags.filter(t => formData.tags.includes(t.id)).length;
                            const isCollapsed = collapsedGroups.has(groupName) && !tagSearch;

                            const toggleCollapse = () => {
                                setCollapsedGroups(prev => {
                                    const next = new Set(prev);
                                    if (next.has(groupName)) next.delete(groupName);
                                    else next.add(groupName);
                                    return next;
                                });
                            };

                            return (
                                <div key={groupName} className="bg-gray-50/50 rounded-xl border border-gray-100 overflow-hidden">
                                    <div
                                        onClick={toggleCollapse}
                                        className="w-full flex items-center justify-between px-4 py-3 hover:bg-gray-100/50 transition-colors cursor-pointer select-none"
                                    >
                                        <span className="flex items-center gap-2 text-sm font-black text-indigo-900 uppercase tracking-wider">
                                            <span className="w-2 h-2 bg-indigo-600 rounded-full"></span>
                                            {groupName}
                                            {selectedCount > 0 && (
                                                <span className="ml-1 px-2 py-0.5 bg-indigo-600 text-white text-[10px] font-bold rounded-full normal-case tracking-normal">
                                                    {selectedCount}
                                                </span>
                                            )}
                                        </span>
                                        <div className="flex items-center gap-2">
                                            <button
                                                type="button"
                                                onClick={(e) => {
                                                    e.stopPropagation();
                                                    setAddingTagGroup(addingTagGroup === groupName ? null : groupName);
                                                    setNewTagName('');
                                                }}
                                                className="p-1 rounded-lg hover:bg-emerald-100 text-emerald-600 hover:text-emerald-700 transition-colors"
                                                title={`Add new tag to ${groupName}`}
                                            >
                                                <Plus className="w-4 h-4" />
                                            </button>
                                            <ChevronDown className={`w-4 h-4 text-gray-400 transition-transform ${isCollapsed ? '' : 'rotate-180'}`} />
                                        </div>
                                    </div>

                                    {/* Inline new tag input */}
                                    {addingTagGroup === groupName && (
                                        <div className="px-4 py-2 bg-emerald-50 border-b border-emerald-100 flex items-center gap-2">
                                            <input
                                                type="text"
                                                value={newTagName}
                                                onChange={(e) => setNewTagName(e.target.value)}
                                                onKeyDown={async (e) => {
                                                    if (e.key === 'Enter') {
                                                        e.preventDefault();
                                                        const name = newTagName.trim();
                                                        if (!name) return;
                                                        try {
                                                            const payload: any = { name };
                                                            const groupId = groupTags[0]?.group;
                                                            if (groupId) payload.group = groupId;
                                                            const res = await api.post('/tags/', payload);
                                                            const created = res.data;
                                                            setTags((prev: Tag[]) => [...prev, created]);
                                                            setFormData((prev: any) => ({ ...prev, tags: [...prev.tags, created.id] }));
                                                            setNewTagName('');
                                                            setAddingTagGroup(null);
                                                        } catch (err: any) {
                                                            alert(`Failed: ${err.response?.data?.name?.[0] || err.response?.data?.detail || err.message}`);
                                                        }
                                                    } else if (e.key === 'Escape') {
                                                        setAddingTagGroup(null);
                                                        setNewTagName('');
                                                    }
                                                }}
                                                placeholder={`New ${groupName.replace(/s$/, '').toLowerCase()} name...`}
                                                autoFocus
                                                className="flex-1 px-3 py-1.5 text-sm border border-emerald-300 rounded-lg bg-white focus:ring-2 focus:ring-emerald-400 focus:border-transparent outline-none text-gray-900"
                                            />
                                            <button
                                                type="button"
                                                onClick={async () => {
                                                    const name = newTagName.trim();
                                                    if (!name) return;
                                                    try {
                                                        const payload: any = { name };
                                                        const groupId = groupTags[0]?.group;
                                                        if (groupId) payload.group = groupId;
                                                        const res = await api.post('/tags/', payload);
                                                        const created = res.data;
                                                        setTags((prev: Tag[]) => [...prev, created]);
                                                        setFormData((prev: any) => ({ ...prev, tags: [...prev.tags, created.id] }));
                                                        setNewTagName('');
                                                        setAddingTagGroup(null);
                                                    } catch (err: any) {
                                                        alert(`Failed: ${err.response?.data?.name?.[0] || err.response?.data?.detail || err.message}`);
                                                    }
                                                }}
                                                className="px-3 py-1.5 bg-emerald-500 text-white rounded-lg text-xs font-bold hover:bg-emerald-600 transition-colors"
                                            >
                                                Add
                                            </button>
                                            <button
                                                type="button"
                                                onClick={() => { setAddingTagGroup(null); setNewTagName(''); }}
                                                className="p-1.5 text-gray-400 hover:text-gray-600 transition-colors"
                                            >
                                                <X className="w-4 h-4" />
                                            </button>
                                        </div>
                                    )}

                                    {!isCollapsed && (
                                        <div className="px-4 pb-4">
                                            {/* Alphabet quick-filter for Manufacturers & Models */}
                                            {ALPHA_GROUPED.includes(groupName) && (() => {
                                                const existingLetters = new Set(filteredTags.map(t => (t.name[0] || '').toUpperCase()));
                                                const activeLetter = letterFilter[groupName] || null;
                                                return (
                                                    <div className="flex flex-wrap gap-1 mb-3 pb-3 border-b border-gray-100">
                                                        <button
                                                            type="button"
                                                            onClick={() => setLetterFilter(prev => ({ ...prev, [groupName]: null }))}
                                                            className={`px-2 py-0.5 rounded text-[11px] font-bold transition-all ${!activeLetter
                                                                ? 'bg-indigo-600 text-white shadow-sm'
                                                                : 'text-gray-400 hover:text-gray-600 hover:bg-gray-100'
                                                                }`}
                                                        >
                                                            All
                                                        </button>
                                                        {'ABCDEFGHIJKLMNOPQRSTUVWXYZ'.split('').map(letter => {
                                                            const hasItems = existingLetters.has(letter);
                                                            const isActive = activeLetter === letter;
                                                            return (
                                                                <button
                                                                    key={letter}
                                                                    type="button"
                                                                    onClick={() => hasItems && setLetterFilter(prev => ({
                                                                        ...prev,
                                                                        [groupName]: isActive ? null : letter
                                                                    }))}
                                                                    className={`w-6 h-6 rounded text-[11px] font-bold transition-all flex items-center justify-center ${isActive
                                                                        ? `${getLetterColor(letter)} text-white shadow-sm`
                                                                        : hasItems
                                                                            ? 'text-gray-600 hover:bg-gray-100 hover:text-gray-900'
                                                                            : 'text-gray-200 cursor-default'
                                                                        }`}
                                                                >
                                                                    {letter}
                                                                </button>
                                                            );
                                                        })}
                                                    </div>
                                                );
                                            })()}

                                            {/* Tag pills */}
                                            <div className="flex flex-wrap gap-2">
                                                {(() => {
                                                    const activeLetter = letterFilter[groupName] || null;
                                                    const visibleTags = ALPHA_GROUPED.includes(groupName) && activeLetter
                                                        ? filteredTags.filter(t => (t.name[0] || '').toUpperCase() === activeLetter)
                                                        : filteredTags;
                                                    return visibleTags.map(renderTagButton);
                                                })()}
                                            </div>
                                        </div>
                                    )}
                                </div>
                            );
                        })}
                </div>
            </div>
        </>
    );
}
