'use client';

import { useState, useEffect } from 'react';
import { Plus, Edit, Trash2, X, Layers, Tag as TagIcon, Filter, ChevronDown, Check } from 'lucide-react';
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

export default function TagsPage() {
  const [activeTab, setActiveTab] = useState<'tags' | 'groups'>('tags');

  // Data
  const [tags, setTags] = useState<Tag[]>([]);
  const [groups, setGroups] = useState<TagGroup[]>([]);
  const [loading, setLoading] = useState(true);

  // Filters
  const [selectedGroupFilter, setSelectedGroupFilter] = useState<number | 'all' | 'ungrouped'>('all');
  const [searchQuery, setSearchQuery] = useState('');

  // Modal State
  const [showTagModal, setShowTagModal] = useState(false);
  const [showGroupModal, setShowGroupModal] = useState(false);
  const [editingTag, setEditingTag] = useState<Tag | null>(null);
  const [editingGroup, setEditingGroup] = useState<TagGroup | null>(null);
  const [activeTagMenuId, setActiveTagMenuId] = useState<number | null>(null);

  // Forms
  const [tagFormData, setTagFormData] = useState({ name: '', slug: '', group: '' as string | number });
  const [groupFormData, setGroupFormData] = useState({ name: '', slug: '', order: 0 });

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
        // Refresh to get updated group_name
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

  const handleQuickGroupAssign = async (tagId: number, groupId: number | null) => {
    try {
      const tag = tags.find(t => t.id === tagId);
      if (!tag) return;

      const response = await api.put(`/tags/${tagId}/`, {
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
      // Update local tags state to remove group link
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

  // Filtered Tags
  const filteredTags = tags.filter(t => {
    // Search filter
    if (searchQuery && !t.name.toLowerCase().includes(searchQuery.toLowerCase())) return false;

    // Group filter
    if (selectedGroupFilter === 'all') return true;
    if (selectedGroupFilter === 'ungrouped') return t.group === null;
    return t.group === selectedGroupFilter;
  });

  return (
    <div className="p-6 max-w-6xl mx-auto min-h-screen bg-gray-50 relative">
      {/* Menu Background Overlay for Quick Select */}
      {activeTagMenuId && (
        <div
          className="fixed inset-0 z-40 bg-transparent"
          onClick={() => setActiveTagMenuId(null)}
        />
      )}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4 mb-6">
        <h1 className="text-2xl sm:text-3xl font-black text-gray-950">
          {activeTab === 'tags' ? 'Tags Manager' : 'Tag Groups'}
        </h1>

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
      </div>

      {loading ? (
        <div className="bg-white rounded-lg shadow-md p-12 text-center">
          <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-indigo-600 mx-auto"></div>
          <p className="text-gray-600 mt-4 font-medium">Loading data...</p>
        </div>
      ) : activeTab === 'tags' ? (
        // --- TAGS VIEW ---
        <div className="space-y-6">
          {/* Filter & Search Bar */}
          <div className="flex flex-col md:flex-row gap-4 items-start md:items-center justify-between">
            {groups.length > 0 && (
              <div className="flex items-center gap-2 overflow-x-auto pb-2 flex-1 min-w-0">
                <Filter size={16} className="text-gray-400 min-w-[16px]" />
                <button
                  onClick={() => setSelectedGroupFilter('all')}
                  className={`px-3 py-1.5 rounded-full text-xs font-bold whitespace-nowrap transition-colors ${selectedGroupFilter === 'all'
                    ? 'bg-indigo-600 text-white'
                    : 'bg-white border border-gray-200 text-gray-600 hover:bg-gray-50'
                    }`}
                >
                  All Tags
                </button>
                <button
                  onClick={() => setSelectedGroupFilter('ungrouped')}
                  className={`px-3 py-1.5 rounded-full text-xs font-bold whitespace-nowrap transition-colors ${selectedGroupFilter === 'ungrouped'
                    ? 'bg-indigo-600 text-white'
                    : 'bg-white border border-gray-200 text-gray-600 hover:bg-gray-50'
                    }`}
                >
                  Uncategorized
                </button>
                {groups.map(group => (
                  <button
                    key={group.id}
                    onClick={() => setSelectedGroupFilter(group.id)}
                    className={`px-3 py-1.5 rounded-full text-xs font-bold whitespace-nowrap transition-colors ${selectedGroupFilter === group.id
                      ? 'bg-indigo-600 text-white'
                      : 'bg-white border border-gray-200 text-gray-600 hover:bg-gray-50'
                      }`}
                  >
                    {group.name}
                  </button>
                ))}
              </div>
            )}

            <div className="relative w-full md:w-64">
              <input
                type="text"
                placeholder="Search tags..."
                value={searchQuery}
                onChange={(e) => setSearchQuery(e.target.value)}
                className="w-full pl-9 pr-4 py-2 bg-white border border-gray-200 rounded-lg text-sm focus:ring-2 focus:ring-indigo-500 outline-none transition-all"
              />
              <Filter size={14} className="absolute left-3 top-1/2 -translate-y-1/2 text-gray-400" />
              {searchQuery && (
                <button
                  onClick={() => setSearchQuery('')}
                  className="absolute right-3 top-1/2 -translate-y-1/2 text-gray-400 hover:text-gray-600"
                >
                  <X size={14} />
                </button>
              )}
            </div>
          </div>

          <div className="bg-white rounded-lg shadow-md overflow-hidden p-6 pb-80">
            {filteredTags.length === 0 ? (
              <div className="text-center py-12">
                <p className="text-gray-500">No tags found.</p>
              </div>
            ) : (
              <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 xl:grid-cols-4 gap-4">
                {filteredTags.map((tag) => (
                  <div
                    key={tag.id}
                    className="bg-gradient-to-br from-indigo-50 to-purple-50 border-2 border-indigo-200 rounded-xl p-4 hover:shadow-lg transition-all group relative"
                  >
                    <div className="flex items-start justify-between gap-4 mb-2">
                      <div>
                        <h3 className="text-lg font-black text-gray-900">{tag.name}</h3>
                        <div className="flex flex-col gap-1">
                          <code className="text-xs text-indigo-600 font-semibold">{tag.slug}</code>

                          <div className="relative mt-1">
                            {tag.group_name ? (
                              <button
                                onClick={() => setActiveTagMenuId(tag.id)}
                                className="flex items-center gap-1 text-[10px] uppercase tracking-wider font-bold text-white bg-indigo-500 px-2 py-1 rounded-full w-fit hover:bg-indigo-600 transition-colors shadow-sm"
                              >
                                {tag.group_name}
                                <ChevronDown size={10} />
                              </button>
                            ) : (
                              <button
                                onClick={() => setActiveTagMenuId(tag.id)}
                                className="flex items-center gap-1 text-[10px] uppercase tracking-wider font-bold text-gray-400 bg-gray-100 border border-dashed border-gray-300 px-2 py-1 rounded-full w-fit hover:bg-gray-200 hover:text-gray-600 hover:border-gray-400 transition-all"
                              >
                                <Plus size={10} />
                                Add to Group
                              </button>
                            )}

                            {/* Quick Select Menu Popover */}
                            {activeTagMenuId === tag.id && (
                              <div className="absolute top-full left-0 mt-2 w-48 bg-white rounded-xl shadow-2xl border border-gray-100 z-50 py-2 max-h-48 overflow-y-auto animate-in fade-in slide-in-from-top-2 duration-200">
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
                        </div>
                      </div>
                      <div className="flex gap-1 opacity-0 group-hover:opacity-100 transition-opacity absolute top-2 right-2 bg-white/80 p-1 rounded-lg backdrop-blur-sm shadow-sm">
                        <button
                          onClick={() => handleEditTag(tag)}
                          className="p-1.5 text-gray-600 hover:text-blue-600 hover:bg-blue-100 rounded-lg transition-colors"
                        >
                          <Edit size={14} />
                        </button>
                        <button
                          onClick={() => handleDeleteTag(tag.id)}
                          className="p-1.5 text-gray-600 hover:text-red-600 hover:bg-red-100 rounded-lg transition-colors"
                        >
                          <Trash2 size={14} />
                        </button>
                      </div>
                    </div>
                    <div className="flex items-center gap-2 mt-2 pt-2 border-t border-indigo-100">
                      <span className="text-xs text-gray-600 font-medium">{tag.article_count} articles</span>
                    </div>
                  </div>
                ))}
              </div>
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
                    <th className="px-6 py-4 font-bold text-gray-900 text-sm">Slug</th>
                    <th className="px-6 py-4 font-bold text-gray-900 text-sm text-right">Actions</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-gray-100">
                  {groups.sort((a, b) => a.order - b.order).map((group) => (
                    <tr key={group.id} className="hover:bg-gray-50 transition-colors">
                      <td className="px-6 py-4 text-gray-600 text-sm font-mono">{group.order}</td>
                      <td className="px-6 py-4">
                        <span className="font-bold text-gray-900">{group.name}</span>
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
                  ))}
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
