import { useState, useEffect } from 'react';
import { X } from 'lucide-react';
import { TagGroup, Tag } from '../types';

interface TagFormModalProps {
    isOpen: boolean;
    onClose: () => void;
    onSave: (payload: { name: string; slug: string; group: number | null }, tagId?: number) => Promise<void>;
    groups: TagGroup[];
    editingTag?: Tag | null;
    initialGroupId?: string | number;
}

export function TagFormModal({ isOpen, onClose, onSave, groups, editingTag, initialGroupId }: TagFormModalProps) {
    const [formData, setFormData] = useState({ name: '', slug: '', group: '' as string | number });
    const [isSaving, setIsSaving] = useState(false);

    useEffect(() => {
        if (isOpen) {
            if (editingTag) {
                setFormData({ name: editingTag.name, slug: editingTag.slug, group: editingTag.group || '' });
            } else {
                setFormData({ name: '', slug: '', group: initialGroupId || '' });
            }
        }
    }, [isOpen, editingTag, initialGroupId]);

    if (!isOpen) return null;

    const generateSlug = (name: string) => {
        return name.toLowerCase().replace(/[^a-z0-9]+/g, '-').replace(/(^-|-$)/g, '');
    };

    const handleNameChange = (name: string) => {
        setFormData({
            ...formData,
            name,
            slug: editingTag ? formData.slug : generateSlug(name),
        });
    };

    const handleSubmit = async (e: React.FormEvent) => {
        e.preventDefault();
        setIsSaving(true);
        try {
            await onSave({
                name: formData.name,
                slug: formData.slug,
                group: formData.group === '' ? null : Number(formData.group),
            }, editingTag?.id);
        } finally {
            setIsSaving(false);
        }
    };

    return (
        <div className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50 p-4">
            <div className="bg-white rounded-xl shadow-2xl max-w-lg w-full p-6" onClick={e => e.stopPropagation()}>
                <div className="flex items-center justify-between mb-6">
                    <h2 className="text-2xl font-black text-gray-950">
                        {editingTag ? 'Edit Tag' : 'New Tag'}
                    </h2>
                    <button onClick={onClose} className="p-2 hover:bg-gray-100 rounded-lg">
                        <X size={24} />
                    </button>
                </div>
                <form onSubmit={handleSubmit} className="space-y-4">
                    <div>
                        <label className="block text-sm font-bold text-gray-900 mb-2">Name *</label>
                        <input
                            type="text"
                            value={formData.name}
                            onChange={(e) => handleNameChange(e.target.value)}
                            className="w-full px-4 py-3 border border-gray-300 rounded-lg focus:ring-2 focus:ring-indigo-500 outline-none text-gray-950"
                            required
                        />
                    </div>
                    <div>
                        <label className="block text-sm font-bold text-gray-900 mb-2">Slug *</label>
                        <input
                            type="text"
                            value={formData.slug}
                            onChange={(e) => setFormData({ ...formData, slug: e.target.value })}
                            className="w-full px-4 py-3 border border-gray-300 rounded-lg focus:ring-2 focus:ring-indigo-500 outline-none text-gray-950"
                            required
                        />
                    </div>
                    <div>
                        <label className="block text-sm font-bold text-gray-900 mb-2">Group</label>
                        <select
                            value={formData.group}
                            onChange={(e) => setFormData({ ...formData, group: e.target.value })}
                            className="w-full px-4 py-3 border border-gray-300 rounded-lg focus:ring-2 focus:ring-indigo-500 outline-none bg-white text-gray-950"
                        >
                            <option value="">No Group</option>
                            {groups.map((g) => (
                                <option key={g.id} value={g.id}>{g.name}</option>
                            ))}
                        </select>
                    </div>
                    <div className="flex gap-4 pt-4">
                        <button
                            type="submit"
                            disabled={isSaving}
                            className="flex-1 bg-indigo-600 text-white py-3 rounded-lg font-bold hover:bg-indigo-700 disabled:opacity-50"
                        >
                            {isSaving ? 'Saving...' : (editingTag ? 'Save Changes' : 'Create Tag')}
                        </button>
                        <button
                            type="button"
                            onClick={onClose}
                            disabled={isSaving}
                            className="px-6 py-3 bg-gray-200 text-gray-800 rounded-lg font-bold hover:bg-gray-300 disabled:opacity-50"
                        >
                            Cancel
                        </button>
                    </div>
                </form>
            </div>
        </div>
    );
}
