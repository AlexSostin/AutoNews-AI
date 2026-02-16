'use client';

import { useState, useEffect, useMemo } from 'react';
import { Plus, Edit, Trash2, X, Layers, Tag as TagIcon, Search, ChevronDown, Check, ArrowUpDown, Hash, Download } from 'lucide-react';
import api from '@/lib/api';

interface TagGroup {
  id: number;
  name: string;
  slug: string;
  order: number;
}

interface Tag {
  id: number;
  name: string;
  slug: string;
  group: number | null;
  group_name: string | null;
  article_count: number;
}

type SortMode = 'alpha' | 'articles';

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

// Groups that get alphabetical sub-grouping
const ALPHA_GROUPED = ['Manufacturers', 'Models'];

export default function TagsPage() {
  const [activeTab, setActiveTab] = useState<'tags' | 'groups'>('tags');

  // Data
  const [tags, setTags] = useState<Tag[]>([]);
  const [groups, setGroups] = useState<TagGroup[]>([]);
  const [loading, setLoading] = useState(true);

  // Search & Sort
  const [searchQuery, setSearchQuery] = useState('');
  const [sortMode, setSortMode] = useState<SortMode>('alpha');
  const [collapsedGroups, setCollapsedGroups] = useState<Set<string>>(new Set());
  const [letterFilter, setLetterFilter] = useState<Record<string, string | null>>({});

  // Modal State
  const [showTagModal, setShowTagModal] = useState(false);
  const [showGroupModal, setShowGroupModal] = useState(false);
  const [editingTag, setEditingTag] = useState<Tag | null>(null);
  const [editingGroup, setEditingGroup] = useState<TagGroup | null>(null);
  const [activeTagMenuId, setActiveTagMenuId] = useState<number | null>(null);

  // Inline edit
  const [inlineEditId, setInlineEditId] = useState<number | null>(null);
  const [inlineEditName, setInlineEditName] = useState('');

  // Forms
  const [tagFormData, setTagFormData] = useState({ name: '', slug: '', group: '' as string | number });
  const [groupFormData, setGroupFormData] = useState({ name: '', slug: '', order: 0 });
  const [exporting, setExporting] = useState(false);

  useEffect(() => {
    fetchData();
  }, []);

  const fetchData = async () => {
    try {
      setLoading(true);
      const [tagsRes, groupsRes] = await Promise.all([
        api.get('/tags/', { params: { _t: Date.now() } }),
        api.get('/tag-groups/', { params: { _t: Date.now() } })
      ]);

      const tagsData = Array.isArray(tagsRes.data) ? tagsRes.data : tagsRes.data.results || [];
      const groupsData = Array.isArray(groupsRes.data) ? groupsRes.data : groupsRes.data.results || [];

      setTags(tagsData);
      setGroups(groupsData);
    } catch (error) {
      console.error('Failed to fetch data:', error);
    } finally {
      setLoading(false);
    }
  };

  // --- Grouped & Filtered Tags ---
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

  // --- Tag Operations ---
  const handleCreateTag = () => {
    setEditingTag(null);
    setTagFormData({ name: '', slug: '', group: '' });
    setShowTagModal(true);
  };

  const handleEditTag = (tag: Tag) => {
    setEditingTag(tag);
    setTagFormData({
      name: tag.name,
      slug: tag.slug,
      group: tag.group || ''
    });
    setShowTagModal(true);
  };

  const handleDeleteTag = async (id: number) => {
    if (!confirm('Are you sure you want to delete this tag?')) return;
    try {
      await api.delete(`/tags/${id}/`);
      setTags(tags.filter(t => t.id !== id));
    } catch (error) {
      alert('Failed to delete tag');
    }
  };

  const handleTagSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    const payload = {
      name: tagFormData.name,
      slug: tagFormData.slug,
      group: tagFormData.group === '' ? null : Number(tagFormData.group)
    };

    try {
      if (editingTag) {
        const response = await api.put(`/tags/${editingTag.id}/`, payload);
        setTags(tags.map(t => t.id === editingTag.id ? { ...t, ...response.data, group_name: groups.find(g => g.id === payload.group)?.name || null } : t));
      } else {
        const response = await api.post('/tags/', payload);
        const newTag = { ...response.data, group_name: groups.find(g => g.id === payload.group)?.name || null };
        setTags([...tags, newTag]);
      }
      setShowTagModal(false);
    } catch (error: any) {
      alert('Failed to save tag: ' + (error.response?.data?.detail || error.message));
    }
  };

  const handleInlineEdit = async (tagId: number) => {
    if (!inlineEditName.trim()) {
      setInlineEditId(null);
      return;
    }
    const tag = tags.find(t => t.id === tagId);
    if (!tag || tag.name === inlineEditName) {
      setInlineEditId(null);
      return;
    }
    try {
      await api.put(`/tags/${tagId}/`, {
        name: inlineEditName,
        slug: tag.slug,
        group: tag.group
      });
      setTags(tags.map(t => t.id === tagId ? { ...t, name: inlineEditName } : t));
    } catch (error) {
      alert('Failed to update tag name');
    }
    setInlineEditId(null);
  };

  const handleQuickGroupAssign = async (tagId: number, groupId: number | null) => {
    try {
      const tag = tags.find(t => t.id === tagId);
      if (!tag) return;

      await api.put(`/tags/${tagId}/`, {
        name: tag.name,
        slug: tag.slug,
        group: groupId
      });

      const updatedGroup = groups.find(g => g.id === groupId);
      setTags(tags.map(t => t.id === tagId ? {
        ...t,
        group: groupId,
        group_name: updatedGroup ? updatedGroup.name : null
      } : t));
      setActiveTagMenuId(null);
    } catch (error) {
      console.error('Quick assign failed:', error);
    }
  };

  // --- Group Operations ---
  const handleCreateGroup = () => {
    setEditingGroup(null);
    setGroupFormData({ name: '', slug: '', order: 0 });
    setShowGroupModal(true);
  };

  const handleEditGroup = (group: TagGroup) => {
    setEditingGroup(group);
    setGroupFormData({
      name: group.name,
      slug: group.slug,
      order: group.order
    });
    setShowGroupModal(true);
  };

  const handleDeleteGroup = async (id: number) => {
    if (!confirm('Delete this group? Tags in this group will be ungrouped.')) return;
    try {
      await api.delete(`/tag-groups/${id}/`);
      setGroups(groups.filter(g => g.id !== id));
      setTags(tags.map(t => t.group === id ? { ...t, group: null, group_name: null } : t));
    } catch (error) {
      alert('Failed to delete group');
    }
  };

  const handleGroupSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    try {
      if (editingGroup) {
        const response = await api.put(`/tag-groups/${editingGroup.id}/`, groupFormData);
        setGroups(groups.map(g => g.id === editingGroup.id ? response.data : g));
      } else {
        const response = await api.post('/tag-groups/', groupFormData);
        setGroups([...groups, response.data]);
      }
      setShowGroupModal(false);
    } catch (error: any) {
      alert('Failed to save group: ' + (error.response?.data?.detail || error.message));
    }
  };

  // --- Export ---
  const handleExportData = async () => {
    try {
      setExporting(true);

      // Fetch all articles (handle pagination)
      let allArticles: any[] = [];
      let page = 1;
      let hasMore = true;
      while (hasMore) {
        try {
          const res = await api.get('/articles/', { params: { page, page_size: 100, _t: Date.now() } });
          const articles = Array.isArray(res.data) ? res.data : res.data.results || [];
          allArticles = [...allArticles, ...articles];
          hasMore = res.data.next ? true : false;
          page++;
        } catch {
          hasMore = false;
        }
      }

      const exportData = {
        exported_at: new Date().toISOString(),
        tags: tags.map(t => ({
          id: t.id,
          name: t.name,
          slug: t.slug,
          group_name: t.group_name,
          article_count: t.article_count,
        })),
        groups: groups.map(g => ({
          id: g.id,
          name: g.name,
          slug: g.slug,
          order: g.order,
        })),
        articles: allArticles.map(a => ({
          id: a.id,
          title: a.title,
          slug: a.slug,
          tags: a.tags || a.tag_names || [],
          categories: a.categories || a.category_names || [],
        })),
      };

      const blob = new Blob([JSON.stringify(exportData, null, 2)], { type: 'application/json' });
      const url = URL.createObjectURL(blob);
      const a = document.createElement('a');
      a.href = url;
      a.download = `freshmotors-data-export-${new Date().toISOString().slice(0, 10)}.json`;
      document.body.appendChild(a);
      a.click();
      document.body.removeChild(a);
      URL.revokeObjectURL(url);
    } catch (error) {
      console.error('Export failed:', error);
      alert('Failed to export data');
    } finally {
      setExporting(false);
    }
  };

  // --- Utilities ---
  const generateSlug = (name: string) => {
    return name.toLowerCase().replace(/[^a-z0-9]+/g, '-').replace(/(^-|-$)/g, '');
  };

  const handleTagNameChange = (name: string) => {
    setTagFormData({
      ...tagFormData,
      name,
      slug: editingTag ? tagFormData.slug : generateSlug(name),
    });
  };

  const handleGroupNameChange = (name: string) => {
    setGroupFormData({
      ...groupFormData,
      name,
      slug: editingGroup ? groupFormData.slug : generateSlug(name),
    });
  };

  return (
    <div className="p-6 max-w-6xl mx-auto min-h-screen bg-gray-50 relative">
      {/* Menu Background Overlay */}
      {activeTagMenuId && (
        <div
          className="fixed inset-0 z-40 bg-transparent"
          onClick={() => setActiveTagMenuId(null)}
        />
      )}

      {/* Header */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4 mb-6">
        <h1 className="text-2xl sm:text-3xl font-black text-gray-950">
          {activeTab === 'tags' ? 'Tags Manager' : 'Tag Groups'}
        </h1>

        <div className="flex items-center gap-3">
          <div className="flex bg-gray-100 p-1 rounded-lg">
            <button
              onClick={() => setActiveTab('tags')}
              className={`px-4 py-2 rounded-md text-sm font-bold transition-all ${activeTab === 'tags'
                ? 'bg-white text-indigo-600 shadow-sm'
                : 'text-gray-600 hover:text-gray-900'
                }`}
            >
              <div className="flex items-center gap-2">
                <TagIcon size={16} />
                <span>Tags ({tags.length})</span>
              </div>
            </button>
            <button
              onClick={() => setActiveTab('groups')}
              className={`px-4 py-2 rounded-md text-sm font-bold transition-all ${activeTab === 'groups'
                ? 'bg-white text-indigo-600 shadow-sm'
                : 'text-gray-600 hover:text-gray-900'
                }`}
            >
              <div className="flex items-center gap-2">
                <Layers size={16} />
                <span>Groups ({groups.length})</span>
              </div>
            </button>
          </div>

          <button
            onClick={activeTab === 'tags' ? handleCreateTag : handleCreateGroup}
            className="bg-gradient-to-r from-indigo-600 to-purple-600 text-white px-4 py-2.5 rounded-lg font-bold hover:from-indigo-700 hover:to-purple-700 transition-all flex items-center justify-center gap-2 shadow-md"
          >
            <Plus size={20} />
            <span>{activeTab === 'tags' ? 'New Tag' : 'New Group'}</span>
          </button>
          <button
            onClick={handleExportData}
            disabled={exporting}
            className="bg-white border-2 border-gray-200 text-gray-700 px-4 py-2.5 rounded-lg font-bold hover:border-indigo-300 hover:text-indigo-600 transition-all flex items-center justify-center gap-2 disabled:opacity-50"
          >
            <Download size={18} />
            <span>{exporting ? 'Exporting...' : 'Export JSON'}</span>
          </button>
        </div>
      </div>

      {loading ? (
        <div className="bg-white rounded-lg shadow-md p-12 text-center">
          <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-indigo-600 mx-auto"></div>
          <p className="text-gray-600 mt-4 font-medium">Loading data...</p>
        </div>
      ) : activeTab === 'tags' ? (
        // --- TAGS VIEW ---
        <div className="space-y-4">
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
                                    onBlur={() => handleInlineEdit(tag.id)}
                                    onKeyDown={(e) => {
                                      if (e.key === 'Enter') handleInlineEdit(tag.id);
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
                                <div className={`items-center gap-0.5 ml-1 ${activeTagMenuId === tag.id ? 'flex' : 'hidden group-hover:flex'}`}>
                                  <button
                                    onClick={() => setActiveTagMenuId(activeTagMenuId === tag.id ? null : tag.id)}
                                    className="p-0.5 text-gray-400 hover:text-indigo-600 transition-colors"
                                    title="Change group"
                                  >
                                    <Layers size={11} />
                                  </button>
                                  <button
                                    onClick={() => handleEditTag(tag)}
                                    className="p-0.5 text-gray-400 hover:text-blue-600 transition-colors"
                                    title="Edit tag"
                                  >
                                    <Edit size={11} />
                                  </button>
                                  <button
                                    onClick={() => handleDeleteTag(tag.id)}
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
                                      onClick={() => handleQuickGroupAssign(tag.id, null)}
                                      className={`w-full text-left px-3 py-2 text-xs hover:bg-gray-50 flex items-center justify-between ${!tag.group ? 'text-indigo-600 bg-indigo-50/30' : 'text-gray-500'}`}
                                    >
                                      No Group
                                      {!tag.group && <Check size={12} className="text-indigo-500" />}
                                    </button>
                                    {groups.map(group => (
                                      <button
                                        key={group.id}
                                        onClick={() => handleQuickGroupAssign(tag.id, group.id)}
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
                              setEditingTag(null);
                              setTagFormData({ name: '', slug: '', group: group?.id || '' });
                              setShowTagModal(true);
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
      ) : (
        // --- GROUPS VIEW ---
        <div className="bg-white rounded-lg shadow-md overflow-hidden">
          {groups.length === 0 ? (
            <div className="p-12 text-center">
              <Layers size={48} className="mx-auto text-gray-300 mb-4" />
              <p className="text-gray-600 font-medium">No tag groups yet.</p>
              <p className="text-sm text-gray-400">Create groups to organize your tags.</p>
            </div>
          ) : (
            <div className="overflow-x-auto">
              <table className="w-full text-left">
                <thead className="bg-gray-50 border-b border-gray-100">
                  <tr>
                    <th className="px-6 py-4 font-bold text-gray-900 text-sm">Order</th>
                    <th className="px-6 py-4 font-bold text-gray-900 text-sm">Name</th>
                    <th className="px-6 py-4 font-bold text-gray-900 text-sm">Tags</th>
                    <th className="px-6 py-4 font-bold text-gray-900 text-sm">Slug</th>
                    <th className="px-6 py-4 font-bold text-gray-900 text-sm text-right">Actions</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-gray-100">
                  {groups.sort((a, b) => a.order - b.order).map((group) => {
                    const tagCount = tags.filter(t => t.group === group.id).length;
                    return (
                      <tr key={group.id} className="hover:bg-gray-50 transition-colors">
                        <td className="px-6 py-4 text-gray-600 text-sm font-mono">{group.order}</td>
                        <td className="px-6 py-4">
                          <span className="font-bold text-gray-900">{group.name}</span>
                        </td>
                        <td className="px-6 py-4">
                          <span className="px-2.5 py-1 bg-indigo-50 text-indigo-700 text-xs font-bold rounded-full">{tagCount}</span>
                        </td>
                        <td className="px-6 py-4 text-gray-500 text-sm font-mono">{group.slug}</td>
                        <td className="px-6 py-4 text-right">
                          <div className="flex items-center justify-end gap-2">
                            <button onClick={() => handleEditGroup(group)} className="text-indigo-600 hover:text-indigo-800 p-1">
                              <Edit size={16} />
                            </button>
                            <button onClick={() => handleDeleteGroup(group.id)} className="text-red-500 hover:text-red-700 p-1">
                              <Trash2 size={16} />
                            </button>
                          </div>
                        </td>
                      </tr>
                    );
                  })}
                </tbody>
              </table>
            </div>
          )}
        </div>
      )}

      {/* Tag Modal */}
      {showTagModal && (
        <div className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50 p-4">
          <div className="bg-white rounded-xl shadow-2xl max-w-lg w-full p-6">
            <div className="flex items-center justify-between mb-6">
              <h2 className="text-2xl font-black text-gray-950">
                {editingTag ? 'Edit Tag' : 'New Tag'}
              </h2>
              <button onClick={() => setShowTagModal(false)} className="p-2 hover:bg-gray-100 rounded-lg">
                <X size={24} />
              </button>
            </div>
            <form onSubmit={handleTagSubmit} className="space-y-4">
              <div>
                <label className="block text-sm font-bold text-gray-900 mb-2">Name *</label>
                <input
                  type="text"
                  value={tagFormData.name}
                  onChange={(e) => handleTagNameChange(e.target.value)}
                  className="w-full px-4 py-3 border border-gray-300 rounded-lg focus:ring-2 focus:ring-indigo-500 outline-none text-gray-950"
                  required
                />
              </div>
              <div>
                <label className="block text-sm font-bold text-gray-900 mb-2">Slug *</label>
                <input
                  type="text"
                  value={tagFormData.slug}
                  onChange={(e) => setTagFormData({ ...tagFormData, slug: e.target.value })}
                  className="w-full px-4 py-3 border border-gray-300 rounded-lg focus:ring-2 focus:ring-indigo-500 outline-none text-gray-950"
                  required
                />
              </div>
              <div>
                <label className="block text-sm font-bold text-gray-900 mb-2">Group</label>
                <select
                  value={tagFormData.group}
                  onChange={(e) => setTagFormData({ ...tagFormData, group: e.target.value })}
                  className="w-full px-4 py-3 border border-gray-300 rounded-lg focus:ring-2 focus:ring-indigo-500 outline-none bg-white text-gray-950"
                >
                  <option value="">No Group</option>
                  {groups.map(g => (
                    <option key={g.id} value={g.id}>{g.name}</option>
                  ))}
                </select>
              </div>
              <div className="flex gap-4 pt-4">
                <button type="submit" className="flex-1 bg-indigo-600 text-white py-3 rounded-lg font-bold hover:bg-indigo-700">
                  {editingTag ? 'Save Changes' : 'Create Tag'}
                </button>
                <button type="button" onClick={() => setShowTagModal(false)} className="px-6 py-3 bg-gray-200 text-gray-800 rounded-lg font-bold hover:bg-gray-300">
                  Cancel
                </button>
              </div>
            </form>
          </div>
        </div>
      )}

      {/* Group Modal */}
      {showGroupModal && (
        <div className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50 p-4">
          <div className="bg-white rounded-xl shadow-2xl max-w-lg w-full p-6">
            <div className="flex items-center justify-between mb-6">
              <h2 className="text-2xl font-black text-gray-950">
                {editingGroup ? 'Edit Group' : 'New Group'}
              </h2>
              <button onClick={() => setShowGroupModal(false)} className="p-2 hover:bg-gray-100 rounded-lg">
                <X size={24} />
              </button>
            </div>
            <form onSubmit={handleGroupSubmit} className="space-y-4">
              <div>
                <label className="block text-sm font-bold text-gray-900 mb-2">Name *</label>
                <input
                  type="text"
                  value={groupFormData.name}
                  onChange={(e) => handleGroupNameChange(e.target.value)}
                  className="w-full px-4 py-3 border border-gray-300 rounded-lg focus:ring-2 focus:ring-indigo-500 outline-none text-gray-950"
                  required
                />
              </div>
              <div>
                <label className="block text-sm font-bold text-gray-900 mb-2">Slug *</label>
                <input
                  type="text"
                  value={groupFormData.slug}
                  onChange={(e) => setGroupFormData({ ...groupFormData, slug: e.target.value })}
                  className="w-full px-4 py-3 border border-gray-300 rounded-lg focus:ring-2 focus:ring-indigo-500 outline-none text-gray-950"
                  required
                />
              </div>
              <div>
                <label className="block text-sm font-bold text-gray-900 mb-2">Order</label>
                <input
                  type="number"
                  value={groupFormData.order}
                  onChange={(e) => setGroupFormData({ ...groupFormData, order: parseInt(e.target.value) || 0 })}
                  className="w-full px-4 py-3 border border-gray-300 rounded-lg focus:ring-2 focus:ring-indigo-500 outline-none text-gray-950"
                />
              </div>
              <div className="flex gap-4 pt-4">
                <button type="submit" className="flex-1 bg-indigo-600 text-white py-3 rounded-lg font-bold hover:bg-indigo-700">
                  {editingGroup ? 'Save Changes' : 'Create Group'}
                </button>
                <button type="button" onClick={() => setShowGroupModal(false)} className="px-6 py-3 bg-gray-200 text-gray-800 rounded-lg font-bold hover:bg-gray-300">
                  Cancel
                </button>
              </div>
            </form>
          </div>
        </div>
      )}
    </div>
  );
}
