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
        <div className="bg-white dark:bg-gray-800 rounded-2xl shadow-sm border border-gray-100 dark:border-gray-700 overflow-hidden">
            <div className="overflow-x-auto">
                <table className="w-full text-sm text-left">
                    <thead className="text-xs text-gray-500 dark:text-gray-400 bg-gray-50/50 dark:bg-gray-800/50 uppercase">
                        <tr>
                            <th className="px-6 py-4 font-medium">User</th>
                            <th className="px-6 py-4 font-medium">Role</th>
                            <th className="px-6 py-4 font-medium">Status</th>
                            <th className="px-6 py-4 font-medium">Joined</th>
                            <th className="px-6 py-4 font-medium">Last Login</th>
                            <th className="px-6 py-4 font-medium text-right">Actions</th>
                        </tr>
                    </thead>
                    <tbody className="divide-y divide-gray-100 dark:divide-gray-700">
                        {users.length === 0 ? (
                            <tr>
                                <td colSpan={6} className="px-6 py-12 text-center text-gray-500 dark:text-gray-400">
                                    <Shield className="mx-auto h-12 w-12 text-gray-300 dark:text-gray-600 mb-3" />
                                    <p className="text-base font-medium text-gray-900 dark:text-white mb-1">No users found</p>
                                    <p>Try adjusting your search or filters</p>
                                </td>
                            </tr>
                        ) : (
                            users.map((user) => (
                                <tr key={user.id} className="hover:bg-gray-50/50 dark:hover:bg-gray-750/50 transition-colors group">
                                    <td className="px-6 py-4 whitespace-nowrap">
                                        <div className="flex flex-col">
                                            <span className="font-medium text-gray-900 dark:text-white flex items-center gap-2">
                                                {user.username}
                                                {currentUser?.username === user.username && (
                                                    <span className="px-2 py-0.5 text-[10px] font-medium bg-blue-100 text-blue-800 dark:bg-blue-900/30 dark:text-blue-300 rounded-full lowercase tracking-wider">
                                                        You
                                                    </span>
                                                )}
                                            </span>
                                            <span className="text-gray-500 dark:text-gray-400 text-xs mt-0.5">{user.email}</span>
                                            {(user.first_name || user.last_name) && (
                                                <span className="text-gray-400 dark:text-gray-500 text-xs mt-0.5">
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
                                            disabled={currentUser?.username === user.username}
                                            className={`inline-flex items-center gap-1.5 px-2.5 py-1 rounded-full text-xs font-medium transition-colors ${user.is_active
                                                    ? 'bg-emerald-100 text-emerald-800 dark:bg-emerald-900/30 dark:text-emerald-300 hover:bg-emerald-200 dark:hover:bg-emerald-900/50 cursor-pointer'
                                                    : 'bg-red-100 text-red-800 dark:bg-red-900/30 dark:text-red-300 hover:bg-red-200 dark:hover:bg-red-900/50 cursor-pointer'
                                                } ${currentUser?.username === user.username ? 'opacity-50 cursor-not-allowed' : ''}`}
                                        >
                                            {user.is_active ? <CheckCircle size={12} /> : <Ban size={12} />}
                                            {user.is_active ? 'Active' : 'Banned'}
                                        </button>
                                    </td>
                                    <td className="px-6 py-4 whitespace-nowrap text-gray-500 dark:text-gray-400">
                                        {formatDate(user.date_joined)}
                                    </td>
                                    <td className="px-6 py-4 whitespace-nowrap text-gray-500 dark:text-gray-400">
                                        {formatDate(user.last_login)}
                                    </td>
                                    <td className="px-6 py-4 whitespace-nowrap text-right">
                                        <div className="flex items-center justify-end gap-2 opacity-0 group-hover:opacity-100 transition-opacity">
                                            {user.new_password && (
                                                <button
                                                    onClick={() => onCopyPassword(user.new_password!, user.id)}
                                                    className={`p-1.5 rounded-lg transition-colors flex items-center gap-1.5 px-3 text-xs font-medium ${copiedId === user.id
                                                            ? 'bg-green-100 text-green-700 dark:bg-green-900/30 dark:text-green-400'
                                                            : 'bg-indigo-50 text-indigo-600 hover:bg-indigo-100 dark:bg-indigo-900/20 dark:text-indigo-400 dark:hover:bg-indigo-900/40'
                                                        }`}
                                                    title="Copy Password"
                                                >
                                                    <Copy size={14} />
                                                    {copiedId === user.id ? 'Copied!' : 'Copy Pass'}
                                                </button>
                                            )}

                                            <button
                                                onClick={() => onChangeRole(user)}
                                                disabled={currentUser?.username === user.username}
                                                className="p-1.5 text-gray-400 hover:text-indigo-600 dark:hover:text-indigo-400 hover:bg-indigo-50 dark:hover:bg-indigo-900/20 rounded-lg transition-colors disabled:opacity-50 disabled:cursor-not-allowed"
                                                title="Change Role"
                                            >
                                                <UserCog size={18} />
                                            </button>

                                            <button
                                                onClick={() => onResetPassword(user)}
                                                className="p-1.5 text-gray-400 hover:text-amber-600 dark:hover:text-amber-400 hover:bg-amber-50 dark:hover:bg-amber-900/20 rounded-lg transition-colors"
                                                title="Reset Password"
                                            >
                                                <KeyRound size={18} />
                                            </button>

                                            <button
                                                onClick={() => onDeleteUser(user)}
                                                disabled={currentUser?.username === user.username || user.is_superuser}
                                                className="p-1.5 text-gray-400 hover:text-red-600 dark:hover:text-red-400 hover:bg-red-50 dark:hover:bg-red-900/20 rounded-lg transition-colors disabled:opacity-50 disabled:cursor-not-allowed"
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
