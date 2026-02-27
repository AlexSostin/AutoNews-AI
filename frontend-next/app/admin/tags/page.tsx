'use client';

import { useState, useEffect } from 'react';
import { Plus, Tag as TagIcon, Layers, Download } from 'lucide-react';
import api from '@/lib/api';
import { TagGroup, Tag } from './types';
import { GroupedTagsView } from './components/GroupedTagsView';
import { TagGroupsTable } from './components/TagGroupsTable';
import { TagFormModal } from './components/TagFormModal';
import { GroupFormModal } from './components/GroupFormModal';

export default function TagsPage() {
  const [activeTab, setActiveTab] = useState<'tags' | 'groups'>('tags');

  // Data
  const [tags, setTags] = useState<Tag[]>([]);
  const [groups, setGroups] = useState<TagGroup[]>([]);
  const [loading, setLoading] = useState(true);

  // Modal State
  const [showTagModal, setShowTagModal] = useState(false);
  const [showGroupModal, setShowGroupModal] = useState(false);
  const [editingTag, setEditingTag] = useState<Tag | null>(null);
  const [editingGroup, setEditingGroup] = useState<TagGroup | null>(null);
  const [initialGroupId, setInitialGroupId] = useState<string | number>('');

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

  // --- Tag Operations ---
  const handleCreateTag = () => {
    setEditingTag(null);
    setInitialGroupId('');
    setShowTagModal(true);
  };

  const handleEditTag = (tag: Tag) => {
    setEditingTag(tag);
    setInitialGroupId(tag.group || '');
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

  const handleSaveTag = async (payload: { name: string; slug: string; group: number | null }, id?: number) => {
    try {
      if (id) {
        const response = await api.put(`/tags/${id}/`, payload);
        setTags(tags.map(t => t.id === id ? { ...t, ...response.data, group_name: groups.find(g => g.id === payload.group)?.name || null } : t));
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

  const handleInlineEdit = async (tagId: number, newName: string) => {
    const tag = tags.find(t => t.id === tagId);
    if (!tag) return;
    try {
      await api.put(`/tags/${tagId}/`, {
        name: newName,
        slug: tag.slug,
        group: tag.group
      });
      setTags(tags.map(t => t.id === tagId ? { ...t, name: newName } : t));
    } catch (error) {
      alert('Failed to update tag name');
      throw error;
    }
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
    } catch (error) {
      console.error('Quick assign failed:', error);
      throw error;
    }
  };

  const handleCreateTagInGroup = (groupId: string | number) => {
    setEditingTag(null);
    setInitialGroupId(groupId);
    setShowTagModal(true);
  };

  // --- Group Operations ---
  const handleCreateGroup = () => {
    setEditingGroup(null);
    setShowGroupModal(true);
  };

  const handleEditGroup = (group: TagGroup) => {
    setEditingGroup(group);
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

  const handleSaveGroup = async (payload: { name: string; slug: string; order: number }, id?: number) => {
    try {
      if (id) {
        const response = await api.put(`/tag-groups/${id}/`, payload);
        setGroups(groups.map(g => g.id === id ? response.data : g));
      } else {
        const response = await api.post('/tag-groups/', payload);
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

  return (
    <div className="p-6 max-w-6xl mx-auto min-h-screen bg-gray-50 relative">
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
        <GroupedTagsView
          tags={tags}
          groups={groups}
          onEditTag={handleEditTag}
          onDeleteTag={handleDeleteTag}
          onInlineEdit={handleInlineEdit}
          onQuickGroupAssign={handleQuickGroupAssign}
          onCreateTagInGroup={handleCreateTagInGroup}
        />
      ) : (
        <TagGroupsTable
          tags={tags}
          groups={groups}
          onEditGroup={handleEditGroup}
          onDeleteGroup={handleDeleteGroup}
        />
      )}

      <TagFormModal
        isOpen={showTagModal}
        onClose={() => setShowTagModal(false)}
        onSave={handleSaveTag}
        groups={groups}
        editingTag={editingTag}
        initialGroupId={initialGroupId}
      />

      <GroupFormModal
        isOpen={showGroupModal}
        onClose={() => setShowGroupModal(false)}
        onSave={handleSaveGroup}
        editingGroup={editingGroup}
      />
    </div>
  );
}
