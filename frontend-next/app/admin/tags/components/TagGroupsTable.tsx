import { Layers, Edit, Trash2 } from 'lucide-react';
import { TagGroup, Tag } from '../types';

interface TagGroupsTableProps {
    groups: TagGroup[];
    tags: Tag[];
    onEditGroup: (group: TagGroup) => void;
    onDeleteGroup: (id: number) => void;
}

export function TagGroupsTable({ groups, tags, onEditGroup, onDeleteGroup }: TagGroupsTableProps) {
    if (groups.length === 0) {
        return (
            <div className="bg-white rounded-lg shadow-md overflow-hidden p-12 text-center">
                <Layers size={48} className="mx-auto text-gray-300 mb-4" />
                <p className="text-gray-600 font-medium">No tag groups yet.</p>
                <p className="text-sm text-gray-400">Create groups to organize your tags.</p>
            </div>
        );
    }

    return (
        <div className="bg-white rounded-lg shadow-md overflow-hidden">
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
                        {[...groups].sort((a, b) => a.order - b.order).map((group) => {
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
                                            <button onClick={() => onEditGroup(group)} className="text-indigo-600 hover:text-indigo-800 p-1">
                                                <Edit size={16} />
                                            </button>
                                            <button onClick={() => onDeleteGroup(group.id)} className="text-red-500 hover:text-red-700 p-1">
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
        </div>
    );
}
