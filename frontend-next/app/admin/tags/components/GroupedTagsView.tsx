import { useState, useMemo } from 'react';
import { Search, X, ArrowUpDown, Hash, ChevronDown, Check, Layers, Edit, Trash2, Plus } from 'lucide-react';
import { TagGroup, Tag } from '../types';

interface GroupedTagsViewProps {
    tags: Tag[];
    groups: TagGroup[];
    onEditTag: (tag: Tag) => void;
    onDeleteTag: (id: number) => void;
    onInlineEdit: (tagId: number, newName: string) => Promise<void>;
    onQuickGroupAssign: (tagId: number, groupId: number | null) => Promise<void>;
    onCreateTagInGroup: (groupId: string | number) => void;
}

// Deterministic color palette for letter avatars
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

type SortMode = 'alpha' | 'articles';

export function GroupedTagsView({
    tags,
    groups,
    onEditTag,
    onDeleteTag,
    onInlineEdit,
    onQuickGroupAssign,
    onCreateTagInGroup
}: GroupedTagsViewProps) {
    const [searchQuery, setSearchQuery] = useState('');
    const [sortMode, setSortMode] = useState<SortMode>('alpha');
    const [collapsedGroups, setCollapsedGroups] = useState<Set<string>>(new Set());
    const [letterFilter, setLetterFilter] = useState<Record<string, string | null>>({});

    const [inlineEditId, setInlineEditId] = useState<number | null>(null);
    const [inlineEditName, setInlineEditName] = useState('');
    const [activeTagMenuId, setActiveTagMenuId] = useState<number | null>(null);

    const groupedTags = useMemo(() => {
        const searchLower = searchQuery.toLowerCase();
        const filtered = searchQuery
            ? tags.filter(t => t.name.toLowerCase().includes(searchLower))
            : tags;

        const sorted = [...filtered].sort((a, b) => {
            if (sortMode === 'articles') return (b.article_count || 0) - (a.article_count || 0);
            return a.name.localeCompare(b.name);
        });

        const grouped: Record<string, Tag[]> = {};
        sorted.forEach(tag => {
            const group = tag.group_name || 'Uncategorized';
            if (!grouped[group]) grouped[group] = [];
            grouped[group].push(tag);
        });

        return Object.entries(grouped).sort(([a], [b]) => {
            if (a === 'Uncategorized') return 1;
            if (b === 'Uncategorized') return -1;
            return a.localeCompare(b);
        });
    }, [tags, searchQuery, sortMode]);

    const toggleGroup = (groupName: string) => {
        setCollapsedGroups(prev => {
            const next = new Set(prev);
            if (next.has(groupName)) next.delete(groupName);
            else next.add(groupName);
            return next;
        });
    };

    const submitInlineEdit = async (tagId: number) => {
        if (!inlineEditName.trim()) {
            setInlineEditId(null);
            return;
        }
        const tag = tags.find(t => t.id === tagId);
        if (!tag || tag.name === inlineEditName) {
            setInlineEditId(null);
            return;
        }
        await onInlineEdit(tagId, inlineEditName);
        setInlineEditId(null);
    };

    return (
        <div className="space-y-4">
            {/* Menu Background Overlay */}
            {activeTagMenuId !== null && (
                <div
                    className="fixed inset-0 z-40 bg-transparent"
                    onClick={() => setActiveTagMenuId(null)}
                />
            )}

            {/* Search & Sort Bar */}
            <div className="flex flex-col sm:flex-row gap-3 items-stretch sm:items-center">
                <div className="relative flex-1">
                    <Search size={16} className="absolute left-3 top-1/2 -translate-y-1/2 text-gray-400" />
                    <input
                        type="text"
                        placeholder="Search tags..."
                        value={searchQuery}
                        onChange={(e) => setSearchQuery(e.target.value)}
                        className="w-full pl-10 pr-10 py-2.5 bg-white border-2 border-gray-200 rounded-xl text-sm focus:border-indigo-400 focus:ring-2 focus:ring-indigo-100 outline-none transition-all text-gray-900 placeholder:text-gray-400"
                    />
                    {searchQuery && (
                        <button
                            onClick={() => setSearchQuery('')}
                            className="absolute right-3 top-1/2 -translate-y-1/2 text-gray-400 hover:text-gray-600"
                        >
                            <X size={14} />
                        </button>
                    )}
                </div>

                {/* Sort Toggle */}
                <div className="flex bg-white border-2 border-gray-200 rounded-xl overflow-hidden">
                    <button
                        onClick={() => setSortMode('alpha')}
                        className={`px-3 py-2 text-xs font-bold flex items-center gap-1.5 transition-colors ${sortMode === 'alpha'
                            ? 'bg-indigo-50 text-indigo-700 border-r-2 border-indigo-200'
                            : 'text-gray-500 hover:bg-gray-50 border-r border-gray-200'
                            }`}
                    >
                        <ArrowUpDown size={12} />
                        A–Z
                    </button>
                    <button
                        onClick={() => setSortMode('articles')}
                        className={`px-3 py-2 text-xs font-bold flex items-center gap-1.5 transition-colors ${sortMode === 'articles'
                            ? 'bg-indigo-50 text-indigo-700'
                            : 'text-gray-500 hover:bg-gray-50'
                            }`}
                    >
                        <Hash size={12} />
                        By Articles
                    </button>
                </div>
            </div>

            {/* Stats Bar */}
            <div className="flex items-center gap-4 text-xs text-gray-500 font-medium px-1">
                <span>{tags.length} total tags</span>
                <span>·</span>
                <span>{groups.length} groups</span>
                <span>·</span>
                <span>{tags.filter(t => !t.group).length} uncategorized</span>
                {searchQuery && (
                    <>
                        <span>·</span>
                        <span className="text-indigo-600">{groupedTags.reduce((sum, [, t]) => sum + t.length, 0)} matching</span>
                    </>
                )}
            </div>

            {/* Grouped Tags */}
            <div className="space-y-2">
                {groupedTags.length === 0 ? (
                    <div className="bg-white rounded-xl shadow-sm p-12 text-center">
                        <p className="text-gray-500">No tags found.</p>
                    </div>
                ) : (
                    groupedTags.map(([groupName, groupTags]) => {
                        const isCollapsed = collapsedGroups.has(groupName) && !searchQuery;
                        const totalArticles = groupTags.reduce((sum, t) => sum + (t.article_count || 0), 0);

                        return (
                            <div key={groupName} className="bg-white rounded-xl shadow-sm border border-gray-100">
                                {/* Group Header */}
                                <button
                                    type="button"
                                    onClick={() => toggleGroup(groupName)}
                                    className="w-full flex items-center justify-between px-5 py-3.5 hover:bg-gray-50/50 transition-colors"
                                >
                                    <div className="flex items-center gap-3">
                                        <span className={`w-2.5 h-2.5 rounded-full ${groupName === 'Uncategorized' ? 'bg-gray-400' : 'bg-indigo-600'}`}></span>
                                        <span className="text-sm font-black text-gray-900 uppercase tracking-wider">
                                            {groupName}
                                        </span>
                                        <span className="px-2 py-0.5 bg-gray-100 text-gray-600 text-[11px] font-bold rounded-full">
                                            {groupTags.length}
                                        </span>
                                        <span className="text-[11px] text-gray-400 font-medium hidden sm:inline">
                                            {totalArticles} articles
                                        </span>
                                    </div>
                                    <ChevronDown className={`w-4 h-4 text-gray-400 transition-transform duration-200 ${isCollapsed ? '' : 'rotate-180'}`} />
                                </button>

                                {/* Tags Grid */}
                                {!isCollapsed && (
                                    <div className="px-5 pb-4">
                                        {/* Alphabet quick-filter bar for Manufacturers & Models */}
                                        {ALPHA_GROUPED.includes(groupName) && (() => {
                                            const existingLetters = new Set(groupTags.map(t => (t.name[0] || '').toUpperCase()));
                                            const activeLetter = letterFilter[groupName] || null;
                                            return (
                                                <div className="flex flex-wrap gap-1 mb-3 pb-3 border-b border-gray-100">
                                                    <button
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
                                                const filtered = ALPHA_GROUPED.includes(groupName) && activeLetter
                                                    ? groupTags.filter(t => (t.name[0] || '').toUpperCase() === activeLetter)
                                                    : groupTags;
                                                return filtered.map(tag => (
                                                    <div
                                                        key={tag.id}
                                                        className="group relative flex items-center gap-1 bg-gradient-to-br from-gray-50 to-gray-100 border border-gray-200 rounded-lg px-3 py-1.5 hover:border-indigo-300 hover:from-indigo-50 hover:to-purple-50 transition-all"
                                                    >
                                                        {inlineEditId === tag.id ? (
                                                            <input
                                                                type="text"
                                                                value={inlineEditName}
                                                                onChange={(e) => setInlineEditName(e.target.value)}
                                                                onBlur={() => submitInlineEdit(tag.id)}
                                                                onKeyDown={(e) => {
                                                                    if (e.key === 'Enter') submitInlineEdit(tag.id);
                                                                    if (e.key === 'Escape') setInlineEditId(null);
                                                                }}
                                                                autoFocus
                                                                className="text-sm font-semibold text-gray-900 bg-transparent outline-none border-b-2 border-indigo-400 w-24"
                                                            />
                                                        ) : (
                                                            <span
                                                                className="text-sm font-semibold text-gray-800 cursor-text"
                                                                onDoubleClick={() => {
                                                                    setInlineEditId(tag.id);
                                                                    setInlineEditName(tag.name);
                                                                }}
                                                                title="Double-click to edit"
                                                            >
                                                                {tag.name}
                                                            </span>
                                                        )}

                                                        {tag.article_count > 0 && (
                                                            <span className="text-[10px] text-gray-400 font-semibold ml-0.5">{tag.article_count}</span>
                                                        )}

                                                        {/* Actions */}
                                                        <div className={`flex items-center gap-0.5 ml-1 ${activeTagMenuId === tag.id ? 'opacity-100' : 'opacity-0 group-hover:opacity-100'} transition-opacity`}>
                                                            <button
                                                                onClick={() => setActiveTagMenuId(activeTagMenuId === tag.id ? null : tag.id)}
                                                                className="p-0.5 text-gray-400 hover:text-indigo-600 transition-colors"
                                                                title="Change group"
                                                            >
                                                                <Layers size={11} />
                                                            </button>
                                                            <button
                                                                onClick={() => onEditTag(tag)}
                                                                className="p-0.5 text-gray-400 hover:text-blue-600 transition-colors"
                                                                title="Edit tag"
                                                            >
                                                                <Edit size={11} />
                                                            </button>
                                                            <button
                                                                onClick={() => onDeleteTag(tag.id)}
                                                                className="p-0.5 text-gray-400 hover:text-red-600 transition-colors"
                                                                title="Delete tag"
                                                            >
                                                                <Trash2 size={11} />
                                                            </button>
                                                        </div>

                                                        {/* Quick Group Assign Popover */}
                                                        {activeTagMenuId === tag.id && (
                                                            <div className="absolute top-full left-0 mt-2 w-48 bg-white rounded-xl shadow-2xl border border-gray-100 z-50 py-2 max-h-48 overflow-y-auto">
                                                                <div className="px-3 py-1 text-[10px] uppercase tracking-widest font-black text-gray-400 border-b border-gray-50 mb-1">
                                                                    Assign Group
                                                                </div>
                                                                <button
                                                                    onClick={async () => {
                                                                        await onQuickGroupAssign(tag.id, null);
                                                                        setActiveTagMenuId(null);
                                                                    }}
                                                                    className={`w-full text-left px-3 py-2 text-xs hover:bg-gray-50 flex items-center justify-between ${!tag.group ? 'text-indigo-600 bg-indigo-50/30' : 'text-gray-500'}`}
                                                                >
                                                                    No Group
                                                                    {!tag.group && <Check size={12} className="text-indigo-500" />}
                                                                </button>
                                                                {groups.map(group => (
                                                                    <button
                                                                        key={group.id}
                                                                        onClick={async () => {
                                                                            await onQuickGroupAssign(tag.id, group.id);
                                                                            setActiveTagMenuId(null);
                                                                        }}
                                                                        className={`w-full text-left px-3 py-2 text-xs hover:bg-indigo-50 flex items-center justify-between ${tag.group === group.id ? 'text-indigo-600 bg-indigo-50 font-bold' : 'text-gray-700'}`}
                                                                    >
                                                                        <span>{group.name}</span>
                                                                        {tag.group === group.id && <Check size={12} className="text-indigo-500" />}
                                                                    </button>
                                                                ))}
                                                            </div>
                                                        )}
                                                    </div>
                                                ));
                                            })()}

                                            {/* Quick add button inside group */}
                                            <button
                                                onClick={() => {
                                                    const group = groups.find(g => g.name === groupName);
                                                    onCreateTagInGroup(group?.id || '');
                                                }}
                                                className="flex items-center gap-1 px-3 py-1.5 border-2 border-dashed border-gray-300 rounded-lg text-sm font-semibold text-gray-400 hover:border-indigo-400 hover:text-indigo-600 hover:bg-indigo-50 transition-all"
                                            >
                                                <Plus size={12} />
                                                Add
                                            </button>
                                        </div>
                                    </div>
                                )}
                            </div>
                        );
                    })
                )}
            </div>
        </div>
    );
}
