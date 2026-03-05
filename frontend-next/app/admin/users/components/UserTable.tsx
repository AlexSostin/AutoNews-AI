import React from 'react';
import {
    Shield, CheckCircle, Ban, UserCog, KeyRound, Copy, Trash2
} from 'lucide-react';
import { UserRoleBadge } from './UserRoleBadge';

interface UserTableProps {
    users: any[];
    onToggleActive: (user: any) => void;
    onChangeRole: (user: any) => void;
    onResetPassword: (user: any) => void;
    onDeleteUser: (user: any) => void;
    onCopyPassword: (password: string, userId: number) => void;
    formatDate: (dateStr: string | null) => string;
    copiedId: number | null;
    currentUser: any;
}

export function UserTable({
    users,
    onToggleActive,
    onChangeRole,
    onResetPassword,
    onDeleteUser,
    onCopyPassword,
    formatDate,
    copiedId,
    currentUser
}: UserTableProps) {
    return (
        <div className="bg-white rounded-2xl shadow-sm border border-gray-100 overflow-hidden">
            <div className="overflow-x-auto">
                <table className="w-full text-sm text-left">
                    <thead className="text-xs text-gray-500 bg-gray-50 uppercase tracking-wider border-b border-gray-100">
                        <tr>
                            <th className="px-6 py-4 font-semibold">User</th>
                            <th className="px-6 py-4 font-semibold">Role</th>
                            <th className="px-6 py-4 font-semibold">Status</th>
                            <th className="px-6 py-4 font-semibold">Joined</th>
                            <th className="px-6 py-4 font-semibold">Last Login</th>
                            <th className="px-6 py-4 font-semibold text-right">Actions</th>
                        </tr>
                    </thead>
                    <tbody className="divide-y divide-gray-50">
                        {users.length === 0 ? (
                            <tr>
                                <td colSpan={6} className="px-6 py-16 text-center text-gray-400">
                                    <Shield className="mx-auto h-12 w-12 text-gray-200 mb-3" />
                                    <p className="text-base font-medium text-gray-700 mb-1">No users found</p>
                                    <p className="text-sm">Try adjusting your search or filters</p>
                                </td>
                            </tr>
                        ) : (
                            users.map((user) => (
                                <tr key={user.id} className="hover:bg-indigo-50/30 transition-colors duration-150 group">
                                    <td className="px-6 py-4 whitespace-nowrap">
                                        <div className="flex flex-col">
                                            <span className="font-semibold text-gray-900 flex items-center gap-2">
                                                {user.username}
                                                {currentUser === user.id && (
                                                    <span className="px-2 py-0.5 text-[10px] font-medium bg-indigo-100 text-indigo-700 rounded-full lowercase tracking-wider">
                                                        You
                                                    </span>
                                                )}
                                            </span>
                                            <span className="text-gray-400 text-xs mt-0.5">{user.email}</span>
                                            {(user.first_name || user.last_name) && (
                                                <span className="text-gray-400 text-xs mt-0.5 italic">
                                                    {user.first_name} {user.last_name}
                                                </span>
                                            )}
                                        </div>
                                    </td>
                                    <td className="px-6 py-4 whitespace-nowrap">
                                        <UserRoleBadge role={user.role} />
                                    </td>
                                    <td className="px-6 py-4 whitespace-nowrap">
                                        <button
                                            onClick={() => onToggleActive(user)}
                                            disabled={currentUser === user.id}
                                            className={`inline-flex items-center gap-1.5 px-3 py-1 rounded-full text-xs font-medium transition-colors ${user.is_active
                                                ? 'bg-emerald-50 text-emerald-700 hover:bg-emerald-100 cursor-pointer'
                                                : 'bg-red-50 text-red-700 hover:bg-red-100 cursor-pointer'
                                                } ${currentUser === user.id ? 'opacity-50 cursor-not-allowed' : ''}`}
                                        >
                                            {user.is_active ? <CheckCircle size={12} /> : <Ban size={12} />}
                                            {user.is_active ? 'Active' : 'Banned'}
                                        </button>
                                    </td>
                                    <td className="px-6 py-4 whitespace-nowrap text-gray-500 text-sm">
                                        {formatDate(user.date_joined)}
                                    </td>
                                    <td className="px-6 py-4 whitespace-nowrap text-gray-500 text-sm">
                                        {formatDate(user.last_login)}
                                    </td>
                                    <td className="px-6 py-4 whitespace-nowrap text-right">
                                        <div className="flex items-center justify-end gap-1.5 opacity-0 group-hover:opacity-100 transition-opacity duration-150">
                                            {user.new_password && (
                                                <button
                                                    onClick={() => onCopyPassword(user.new_password!, user.id)}
                                                    className={`p-1.5 rounded-lg transition-colors flex items-center gap-1.5 px-3 text-xs font-medium ${copiedId === user.id
                                                        ? 'bg-green-100 text-green-700'
                                                        : 'bg-indigo-50 text-indigo-600 hover:bg-indigo-100'
                                                        }`}
                                                    title="Copy Password"
                                                >
                                                    <Copy size={14} />
                                                    {copiedId === user.id ? 'Copied!' : 'Copy Pass'}
                                                </button>
                                            )}

                                            <button
                                                onClick={() => onChangeRole(user)}
                                                disabled={currentUser === user.id}
                                                className="p-1.5 text-gray-400 hover:text-indigo-600 hover:bg-indigo-50 rounded-lg transition-colors disabled:opacity-40 disabled:cursor-not-allowed"
                                                title="Change Role"
                                            >
                                                <UserCog size={18} />
                                            </button>

                                            <button
                                                onClick={() => onResetPassword(user)}
                                                className="p-1.5 text-gray-400 hover:text-amber-600 hover:bg-amber-50 rounded-lg transition-colors"
                                                title="Reset Password"
                                            >
                                                <KeyRound size={18} />
                                            </button>

                                            <button
                                                onClick={() => onDeleteUser(user)}
                                                disabled={currentUser === user.id || user.is_superuser}
                                                className="p-1.5 text-gray-400 hover:text-red-600 hover:bg-red-50 rounded-lg transition-colors disabled:opacity-40 disabled:cursor-not-allowed"
                                                title="Delete User"
                                            >
                                                <Trash2 size={18} />
                                            </button>
                                        </div>
                                    </td>
                                </tr>
                            ))
                        )}
                    </tbody>
                </table>
            </div>
        </div>
    );
}
