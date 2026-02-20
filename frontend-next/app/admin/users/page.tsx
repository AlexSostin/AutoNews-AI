'use client';

import { useState, useEffect } from 'react';
import {
    Users,
    Search,
    Shield,
    ShieldCheck,
    ShieldAlert,
    UserCog,
    Trash2,
    KeyRound,
    Ban,
    CheckCircle,
    Loader2,
    Copy,
    Check,
    X,
    Crown,
    UserCheck,
    User as UserIcon,
    AlertTriangle,
    ChevronLeft,
    ChevronRight,
    UserPlus,
    Eye,
    EyeOff
} from 'lucide-react';
import { authenticatedFetch } from '@/lib/authenticatedFetch';
import { isSuperuser } from '@/lib/auth';

interface UserData {
    id: number;
    username: string;
    email: string;
    first_name: string;
    last_name: string;
    role: 'Superuser' | 'Staff' | 'User';
    is_superuser: boolean;
    is_staff: boolean;
    is_active: boolean;
    date_joined: string;
    last_login: string | null;
}

interface Stats {
    total: number;
    active: number;
    staff: number;
    superusers: number;
}

interface Pagination {
    page: number;
    page_size: number;
    total_count: number;
    total_pages: number;
}

export default function UsersPage() {
    const [users, setUsers] = useState<UserData[]>([]);
    const [stats, setStats] = useState<Stats>({ total: 0, active: 0, staff: 0, superusers: 0 });
    const [pagination, setPagination] = useState<Pagination>({ page: 1, page_size: 25, total_count: 0, total_pages: 1 });
    const [loading, setLoading] = useState(true);
    const [search, setSearch] = useState('');
    const [roleFilter, setRoleFilter] = useState('');
    const [statusFilter, setStatusFilter] = useState('');
    const [page, setPage] = useState(1);
    const [actionLoading, setActionLoading] = useState<number | null>(null);
    const [accessDenied, setAccessDenied] = useState(false);

    // Modal states
    const [deleteModal, setDeleteModal] = useState<UserData | null>(null);
    const [resetModal, setResetModal] = useState<UserData | null>(null);
    const [newPassword, setNewPassword] = useState('');
    const [copied, setCopied] = useState(false);
    const [editModal, setEditModal] = useState<UserData | null>(null);
    const [editRole, setEditRole] = useState('');

    // Create user modal
    const [createModal, setCreateModal] = useState(false);
    const [createForm, setCreateForm] = useState({ username: '', email: '', first_name: '', last_name: '', password: '', role: 'user' });
    const [createLoading, setCreateLoading] = useState(false);
    const [createError, setCreateError] = useState('');
    const [showCreatePassword, setShowCreatePassword] = useState(false);

    // Current user
    const [currentUserId, setCurrentUserId] = useState<number | null>(null);

    // Access check
    useEffect(() => {
        if (!isSuperuser()) {
            setAccessDenied(true);
            setLoading(false);
        }
    }, []);

    // Reset page on filter/search change
    useEffect(() => {
        setPage(1);
    }, [search, roleFilter, statusFilter]);

    useEffect(() => {
        if (!accessDenied) {
            fetchCurrentUser();
            fetchUsers();
        }
    }, [search, roleFilter, statusFilter, page, accessDenied]);

    const fetchCurrentUser = async () => {
        try {
            const res = await authenticatedFetch('/users/me/');
            if (res.ok) {
                const data = await res.json();
                setCurrentUserId(data.id);
            }
        } catch (e) {
            console.error('Failed to fetch current user', e);
        }
    };

    const fetchUsers = async () => {
        setLoading(true);
        try {
            const params = new URLSearchParams();
            if (search) params.set('search', search);
            if (roleFilter) params.set('role', roleFilter);
            if (statusFilter) params.set('is_active', statusFilter);
            params.set('page', String(page));
            params.set('page_size', '25');

            const res = await authenticatedFetch(`/admin/users/?${params.toString()}`);
            if (res.ok) {
                const data = await res.json();
                setUsers(data.results || []);
                setStats(data.stats || { total: 0, active: 0, staff: 0, superusers: 0 });
                if (data.pagination) setPagination(data.pagination);
            }
        } catch (e) {
            console.error('Failed to fetch users', e);
        } finally {
            setLoading(false);
        }
    };

    const toggleActive = async (user: UserData) => {
        if (user.id === currentUserId) return;
        setActionLoading(user.id);
        try {
            const res = await authenticatedFetch(`/admin/users/${user.id}/`, {
                method: 'PATCH',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ is_active: !user.is_active }),
            });
            if (res.ok) {
                fetchUsers();
            } else {
                const err = await res.json();
                alert(err.detail || 'Failed to update user');
            }
        } catch (e) {
            console.error('Failed to toggle active', e);
        } finally {
            setActionLoading(null);
        }
    };

    const changeRole = async () => {
        if (!editModal || !editRole) return;
        setActionLoading(editModal.id);
        try {
            const res = await authenticatedFetch(`/admin/users/${editModal.id}/`, {
                method: 'PATCH',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ role: editRole }),
            });
            if (res.ok) {
                setEditModal(null);
                fetchUsers();
            } else {
                const err = await res.json();
                alert(err.detail || 'Failed to change role');
            }
        } catch (e) {
            console.error('Failed to change role', e);
        } finally {
            setActionLoading(null);
        }
    };

    const resetPassword = async () => {
        if (!resetModal) return;
        setActionLoading(resetModal.id);
        try {
            const res = await authenticatedFetch(`/admin/users/${resetModal.id}/reset-password/`, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
            });
            if (res.ok) {
                const data = await res.json();
                setNewPassword(data.new_password);
            } else {
                const err = await res.json();
                alert(err.detail || 'Failed to reset password');
            }
        } catch (e) {
            console.error('Failed to reset password', e);
        } finally {
            setActionLoading(null);
        }
    };

    const deleteUser = async () => {
        if (!deleteModal) return;
        setActionLoading(deleteModal.id);
        try {
            const res = await authenticatedFetch(`/admin/users/${deleteModal.id}/`, {
                method: 'DELETE',
            });
            if (res.ok) {
                setDeleteModal(null);
                fetchUsers();
            } else {
                const err = await res.json();
                alert(err.detail || 'Failed to delete user');
            }
        } catch (e) {
            console.error('Failed to delete user', e);
        } finally {
            setActionLoading(null);
        }
    };

    const copyPassword = () => {
        navigator.clipboard.writeText(newPassword);
        setCopied(true);
        setTimeout(() => setCopied(false), 2000);
    };

    const createUser = async () => {
        setCreateLoading(true);
        setCreateError('');
        try {
            const res = await authenticatedFetch('/api/v1/admin/users/', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify(createForm),
            });
            if (res.ok) {
                setCreateModal(false);
                fetchUsers();
            } else {
                const err = await res.json();
                setCreateError(err.error || 'Failed to create user');
            }
        } catch (e) {
            setCreateError('Network error. Please try again.');
        } finally {
            setCreateLoading(false);
        }
    };

    const getRoleBadge = (role: string) => {
        switch (role) {
            case 'Superuser':
                return (
                    <span className="inline-flex items-center gap-1 px-2.5 py-1 rounded-full text-xs font-bold bg-gradient-to-r from-amber-100 to-orange-100 text-amber-800 border border-amber-200">
                        <Crown size={12} /> Superuser
                    </span>
                );
            case 'Staff':
                return (
                    <span className="inline-flex items-center gap-1 px-2.5 py-1 rounded-full text-xs font-bold bg-gradient-to-r from-blue-100 to-indigo-100 text-blue-800 border border-blue-200">
                        <ShieldCheck size={12} /> Staff
                    </span>
                );
            default:
                return (
                    <span className="inline-flex items-center gap-1 px-2.5 py-1 rounded-full text-xs font-medium bg-gray-100 text-gray-600 border border-gray-200">
                        <UserIcon size={12} /> User
                    </span>
                );
        }
    };

    const formatDate = (dateStr: string | null) => {
        if (!dateStr) return 'Never';
        const d = new Date(dateStr);
        return d.toLocaleDateString('en-US', { year: 'numeric', month: 'short', day: 'numeric' });
    };

    return (
        <div className="space-y-6">
            {/* Access Denied */}
            {accessDenied && (
                <div className="flex flex-col items-center justify-center py-20">
                    <ShieldAlert size={48} className="text-red-400 mb-4" />
                    <h2 className="text-xl font-bold text-gray-900 mb-2">Access Denied</h2>
                    <p className="text-gray-500 text-center max-w-md">Only superusers can manage users. Contact your administrator if you need access.</p>
                </div>
            )}

            {!accessDenied && (
                <>
                    {/* Header */}
                    <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-4">
                        <div>
                            <h1 className="text-2xl sm:text-3xl font-black bg-gradient-to-r from-indigo-600 to-purple-600 bg-clip-text text-transparent">
                                User Management
                            </h1>
                            <p className="text-gray-500 mt-1">Manage users, roles, and permissions</p>
                        </div>
                        <button
                            onClick={() => { setCreateModal(true); setCreateForm({ username: '', email: '', first_name: '', last_name: '', password: '', role: 'user' }); setCreateError(''); }}
                            className="inline-flex items-center gap-2 px-5 py-2.5 bg-gradient-to-r from-indigo-600 to-purple-600 text-white rounded-xl font-semibold text-sm hover:from-indigo-700 hover:to-purple-700 transition-all shadow-md hover:shadow-lg"
                        >
                            <UserPlus size={18} />
                            Add User
                        </button>
                    </div>

                    {/* Stats Cards */}
                    <div className="grid grid-cols-2 sm:grid-cols-4 gap-4">
                        <div className="bg-white rounded-xl shadow-sm border border-gray-100 p-4 hover:shadow-md transition-shadow">
                            <div className="flex items-center gap-3">
                                <div className="p-2.5 rounded-lg bg-gradient-to-br from-indigo-100 to-purple-100">
                                    <Users size={20} className="text-indigo-600" />
                                </div>
                                <div>
                                    <p className="text-2xl font-black text-gray-900">{stats.total}</p>
                                    <p className="text-xs text-gray-500 font-medium">Total Users</p>
                                </div>
                            </div>
                        </div>
                        <div className="bg-white rounded-xl shadow-sm border border-gray-100 p-4 hover:shadow-md transition-shadow">
                            <div className="flex items-center gap-3">
                                <div className="p-2.5 rounded-lg bg-gradient-to-br from-green-100 to-emerald-100">
                                    <UserCheck size={20} className="text-green-600" />
                                </div>
                                <div>
                                    <p className="text-2xl font-black text-gray-900">{stats.active}</p>
                                    <p className="text-xs text-gray-500 font-medium">Active</p>
                                </div>
                            </div>
                        </div>
                        <div className="bg-white rounded-xl shadow-sm border border-gray-100 p-4 hover:shadow-md transition-shadow">
                            <div className="flex items-center gap-3">
                                <div className="p-2.5 rounded-lg bg-gradient-to-br from-blue-100 to-indigo-100">
                                    <ShieldCheck size={20} className="text-blue-600" />
                                </div>
                                <div>
                                    <p className="text-2xl font-black text-gray-900">{stats.staff}</p>
                                    <p className="text-xs text-gray-500 font-medium">Staff</p>
                                </div>
                            </div>
                        </div>
                        <div className="bg-white rounded-xl shadow-sm border border-gray-100 p-4 hover:shadow-md transition-shadow">
                            <div className="flex items-center gap-3">
                                <div className="p-2.5 rounded-lg bg-gradient-to-br from-amber-100 to-orange-100">
                                    <Crown size={20} className="text-amber-600" />
                                </div>
                                <div>
                                    <p className="text-2xl font-black text-gray-900">{stats.superusers}</p>
                                    <p className="text-xs text-gray-500 font-medium">Superusers</p>
                                </div>
                            </div>
                        </div>
                    </div>

                    {/* Search & Filters */}
                    <div className="bg-white rounded-xl shadow-sm border border-gray-100 p-4">
                        <div className="flex flex-col sm:flex-row gap-3">
                            <div className="relative flex-1">
                                <Search size={18} className="absolute left-3 top-1/2 -translate-y-1/2 text-gray-400" />
                                <input
                                    type="text"
                                    value={search}
                                    onChange={(e) => setSearch(e.target.value)}
                                    placeholder="Search by username, email, or name..."
                                    className="w-full pl-10 pr-4 py-2.5 border border-gray-200 rounded-lg focus:ring-2 focus:ring-indigo-500 focus:border-indigo-500 outline-none transition text-sm text-gray-900"
                                />
                            </div>
                            <select
                                value={roleFilter}
                                onChange={(e) => setRoleFilter(e.target.value)}
                                className="px-4 py-2.5 border border-gray-200 rounded-lg focus:ring-2 focus:ring-indigo-500 focus:border-indigo-500 outline-none text-sm text-gray-900 bg-white cursor-pointer"
                            >
                                <option value="">All Roles</option>
                                <option value="superuser">Superusers</option>
                                <option value="staff">Staff</option>
                                <option value="user">Regular Users</option>
                            </select>
                            <select
                                value={statusFilter}
                                onChange={(e) => setStatusFilter(e.target.value)}
                                className="px-4 py-2.5 border border-gray-200 rounded-lg focus:ring-2 focus:ring-indigo-500 focus:border-indigo-500 outline-none text-sm text-gray-900 bg-white cursor-pointer"
                            >
                                <option value="">All Status</option>
                                <option value="true">Active</option>
                                <option value="false">Inactive / Banned</option>
                            </select>
                        </div>
                    </div>

                    {/* Users Table */}
                    <div className="bg-white rounded-xl shadow-sm border border-gray-100 overflow-hidden">
                        {loading ? (
                            <div className="flex items-center justify-center py-20">
                                <Loader2 className="animate-spin text-indigo-500" size={32} />
                            </div>
                        ) : users.length === 0 ? (
                            <div className="text-center py-20 text-gray-500">
                                <Users size={48} className="mx-auto mb-3 opacity-30" />
                                <p className="font-medium">No users found</p>
                                <p className="text-sm mt-1">Try adjusting your search or filters</p>
                            </div>
                        ) : (
                            <div className="overflow-x-auto">
                                <table className="w-full">
                                    <thead>
                                        <tr className="bg-gray-50/80 border-b border-gray-100">
                                            <th className="text-left px-5 py-3.5 text-xs font-semibold text-gray-500 uppercase tracking-wider">User</th>
                                            <th className="text-left px-5 py-3.5 text-xs font-semibold text-gray-500 uppercase tracking-wider">Role</th>
                                            <th className="text-left px-5 py-3.5 text-xs font-semibold text-gray-500 uppercase tracking-wider">Status</th>
                                            <th className="text-left px-5 py-3.5 text-xs font-semibold text-gray-500 uppercase tracking-wider hidden md:table-cell">Joined</th>
                                            <th className="text-left px-5 py-3.5 text-xs font-semibold text-gray-500 uppercase tracking-wider hidden lg:table-cell">Last Login</th>
                                            <th className="text-right px-5 py-3.5 text-xs font-semibold text-gray-500 uppercase tracking-wider">Actions</th>
                                        </tr>
                                    </thead>
                                    <tbody className="divide-y divide-gray-50">
                                        {users.map((user) => {
                                            const isSelf = user.id === currentUserId;
                                            return (
                                                <tr key={user.id} className={`hover:bg-gray-50/50 transition-colors ${!user.is_active ? 'opacity-60' : ''}`}>
                                                    {/* User info */}
                                                    <td className="px-5 py-4">
                                                        <div className="flex items-center gap-3">
                                                            <div className={`w-10 h-10 rounded-full flex items-center justify-center text-white font-bold text-sm ${user.is_superuser
                                                                ? 'bg-gradient-to-br from-amber-400 to-orange-500'
                                                                : user.is_staff
                                                                    ? 'bg-gradient-to-br from-blue-400 to-indigo-500'
                                                                    : 'bg-gradient-to-br from-gray-400 to-gray-500'
                                                                }`}>
                                                                {user.username.charAt(0).toUpperCase()}
                                                            </div>
                                                            <div>
                                                                <div className="font-semibold text-gray-900 flex items-center gap-1.5">
                                                                    {user.username}
                                                                    {isSelf && (
                                                                        <span className="text-[10px] font-bold bg-indigo-100 text-indigo-700 px-1.5 py-0.5 rounded-full">YOU</span>
                                                                    )}
                                                                </div>
                                                                <div className="text-sm text-gray-500">{user.email}</div>
                                                            </div>
                                                        </div>
                                                    </td>

                                                    {/* Role */}
                                                    <td className="px-5 py-4">{getRoleBadge(user.role)}</td>

                                                    {/* Status */}
                                                    <td className="px-5 py-4">
                                                        {user.is_active ? (
                                                            <span className="inline-flex items-center gap-1 text-xs font-medium text-green-700 bg-green-50 px-2 py-1 rounded-full">
                                                                <CheckCircle size={12} /> Active
                                                            </span>
                                                        ) : (
                                                            <span className="inline-flex items-center gap-1 text-xs font-medium text-red-700 bg-red-50 px-2 py-1 rounded-full">
                                                                <Ban size={12} /> Banned
                                                            </span>
                                                        )}
                                                    </td>

                                                    {/* Joined */}
                                                    <td className="px-5 py-4 text-sm text-gray-500 hidden md:table-cell">
                                                        {formatDate(user.date_joined)}
                                                    </td>

                                                    {/* Last login */}
                                                    <td className="px-5 py-4 text-sm text-gray-500 hidden lg:table-cell">
                                                        {formatDate(user.last_login)}
                                                    </td>

                                                    {/* Actions */}
                                                    <td className="px-5 py-4">
                                                        <div className="flex items-center justify-end gap-1">
                                                            {/* Change Role */}
                                                            <button
                                                                onClick={() => { setEditModal(user); setEditRole(user.role.toLowerCase()); }}
                                                                disabled={isSelf || actionLoading === user.id}
                                                                className="p-2 rounded-lg text-gray-400 hover:text-indigo-600 hover:bg-indigo-50 transition-colors disabled:opacity-30 disabled:cursor-not-allowed"
                                                                title="Change Role"
                                                            >
                                                                <ShieldAlert size={16} />
                                                            </button>

                                                            {/* Toggle Active */}
                                                            <button
                                                                onClick={() => toggleActive(user)}
                                                                disabled={isSelf || actionLoading === user.id}
                                                                className={`p-2 rounded-lg transition-colors disabled:opacity-30 disabled:cursor-not-allowed ${user.is_active
                                                                    ? 'text-gray-400 hover:text-amber-600 hover:bg-amber-50'
                                                                    : 'text-gray-400 hover:text-green-600 hover:bg-green-50'
                                                                    }`}
                                                                title={user.is_active ? 'Ban User' : 'Unban User'}
                                                            >
                                                                {actionLoading === user.id ? (
                                                                    <Loader2 size={16} className="animate-spin" />
                                                                ) : user.is_active ? (
                                                                    <Ban size={16} />
                                                                ) : (
                                                                    <CheckCircle size={16} />
                                                                )}
                                                            </button>

                                                            {/* Reset Password */}
                                                            <button
                                                                onClick={() => { setResetModal(user); setNewPassword(''); setCopied(false); }}
                                                                disabled={actionLoading === user.id}
                                                                className="p-2 rounded-lg text-gray-400 hover:text-purple-600 hover:bg-purple-50 transition-colors disabled:opacity-30"
                                                                title="Reset Password"
                                                            >
                                                                <KeyRound size={16} />
                                                            </button>

                                                            {/* Delete */}
                                                            <button
                                                                onClick={() => setDeleteModal(user)}
                                                                disabled={isSelf || actionLoading === user.id}
                                                                className="p-2 rounded-lg text-gray-400 hover:text-red-600 hover:bg-red-50 transition-colors disabled:opacity-30 disabled:cursor-not-allowed"
                                                                title="Delete User"
                                                            >
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

                        {/* Pagination */}
                        {!loading && pagination.total_pages > 1 && (
                            <div className="flex items-center justify-between px-5 py-4 border-t border-gray-100 bg-gray-50/50">
                                <p className="text-sm text-gray-600">
                                    Showing <strong>{(pagination.page - 1) * pagination.page_size + 1}</strong>–<strong>{Math.min(pagination.page * pagination.page_size, pagination.total_count)}</strong> of <strong>{pagination.total_count}</strong> users
                                </p>
                                <div className="flex items-center gap-1">
                                    <button
                                        onClick={() => setPage(p => Math.max(1, p - 1))}
                                        disabled={page <= 1}
                                        className="p-2 rounded-lg text-gray-500 hover:bg-gray-200 transition-colors disabled:opacity-30 disabled:cursor-not-allowed"
                                    >
                                        <ChevronLeft size={18} />
                                    </button>
                                    {Array.from({ length: Math.min(5, pagination.total_pages) }, (_, i) => {
                                        let pageNum: number;
                                        if (pagination.total_pages <= 5) {
                                            pageNum = i + 1;
                                        } else if (page <= 3) {
                                            pageNum = i + 1;
                                        } else if (page >= pagination.total_pages - 2) {
                                            pageNum = pagination.total_pages - 4 + i;
                                        } else {
                                            pageNum = page - 2 + i;
                                        }
                                        return (
                                            <button
                                                key={pageNum}
                                                onClick={() => setPage(pageNum)}
                                                className={`w-9 h-9 rounded-lg text-sm font-medium transition-colors ${pageNum === page
                                                    ? 'bg-indigo-600 text-white'
                                                    : 'text-gray-600 hover:bg-gray-200'
                                                    }`}
                                            >
                                                {pageNum}
                                            </button>
                                        );
                                    })}
                                    <button
                                        onClick={() => setPage(p => Math.min(pagination.total_pages, p + 1))}
                                        disabled={page >= pagination.total_pages}
                                        className="p-2 rounded-lg text-gray-500 hover:bg-gray-200 transition-colors disabled:opacity-30 disabled:cursor-not-allowed"
                                    >
                                        <ChevronRight size={18} />
                                    </button>
                                </div>
                            </div>
                        )}
                    </div>

                    {/* Delete Confirmation Modal */}
                    {deleteModal && (
                        <div className="fixed inset-0 bg-black/50 backdrop-blur-sm z-50 flex items-center justify-center p-4" onClick={() => setDeleteModal(null)}>
                            <div className="bg-white rounded-2xl shadow-2xl max-w-md w-full p-6" onClick={(e) => e.stopPropagation()}>
                                <div className="flex items-center gap-3 mb-4">
                                    <div className="p-3 rounded-full bg-red-100">
                                        <AlertTriangle size={24} className="text-red-600" />
                                    </div>
                                    <div>
                                        <h3 className="text-lg font-bold text-gray-900">Delete User</h3>
                                        <p className="text-sm text-gray-500">This action cannot be undone</p>
                                    </div>
                                </div>
                                <p className="text-gray-700 mb-6">
                                    Are you sure you want to delete <strong>{deleteModal.username}</strong> ({deleteModal.email})?
                                    All their data including comments and favorites will be removed.
                                </p>
                                <div className="flex gap-3 justify-end">
                                    <button
                                        onClick={() => setDeleteModal(null)}
                                        className="px-4 py-2 text-sm font-medium text-gray-700 bg-gray-100 rounded-lg hover:bg-gray-200 transition-colors"
                                    >
                                        Cancel
                                    </button>
                                    <button
                                        onClick={deleteUser}
                                        disabled={actionLoading === deleteModal.id}
                                        className="px-4 py-2 text-sm font-medium text-white bg-red-600 rounded-lg hover:bg-red-700 transition-colors disabled:opacity-50 flex items-center gap-2"
                                    >
                                        {actionLoading === deleteModal.id && <Loader2 size={14} className="animate-spin" />}
                                        Delete User
                                    </button>
                                </div>
                            </div>
                        </div>
                    )}

                    {/* Reset Password Modal */}
                    {resetModal && (
                        <div className="fixed inset-0 bg-black/50 backdrop-blur-sm z-50 flex items-center justify-center p-4" onClick={() => { setResetModal(null); setNewPassword(''); }}>
                            <div className="bg-white rounded-2xl shadow-2xl max-w-md w-full p-6" onClick={(e) => e.stopPropagation()}>
                                <div className="flex items-center justify-between mb-4">
                                    <div className="flex items-center gap-3">
                                        <div className="p-3 rounded-full bg-purple-100">
                                            <KeyRound size={24} className="text-purple-600" />
                                        </div>
                                        <div>
                                            <h3 className="text-lg font-bold text-gray-900">Reset Password</h3>
                                            <p className="text-sm text-gray-500">{resetModal.username}</p>
                                        </div>
                                    </div>
                                    <button onClick={() => { setResetModal(null); setNewPassword(''); }} className="p-1 hover:bg-gray-100 rounded-lg">
                                        <X size={20} className="text-gray-400" />
                                    </button>
                                </div>

                                {!newPassword ? (
                                    <>
                                        <p className="text-gray-700 mb-6">
                                            Generate a new random password for <strong>{resetModal.username}</strong>?
                                            The new password will be shown only once.
                                        </p>
                                        <div className="flex gap-3 justify-end">
                                            <button
                                                onClick={() => { setResetModal(null); setNewPassword(''); }}
                                                className="px-4 py-2 text-sm font-medium text-gray-700 bg-gray-100 rounded-lg hover:bg-gray-200 transition-colors"
                                            >
                                                Cancel
                                            </button>
                                            <button
                                                onClick={resetPassword}
                                                disabled={actionLoading === resetModal.id}
                                                className="px-4 py-2 text-sm font-medium text-white bg-purple-600 rounded-lg hover:bg-purple-700 transition-colors disabled:opacity-50 flex items-center gap-2"
                                            >
                                                {actionLoading === resetModal.id && <Loader2 size={14} className="animate-spin" />}
                                                Generate Password
                                            </button>
                                        </div>
                                    </>
                                ) : (
                                    <>
                                        <div className="mb-4">
                                            <label className="text-xs font-medium text-gray-500 mb-1.5 block">New Password (copy it now!)</label>
                                            <div className="flex items-center gap-2">
                                                <code className="flex-1 px-3 py-2.5 bg-gray-900 text-green-400 rounded-lg font-mono text-sm select-all">
                                                    {newPassword}
                                                </code>
                                                <button
                                                    onClick={copyPassword}
                                                    className={`p-2.5 rounded-lg transition-colors ${copied
                                                        ? 'bg-green-100 text-green-600'
                                                        : 'bg-gray-100 text-gray-600 hover:bg-gray-200'
                                                        }`}
                                                >
                                                    {copied ? <Check size={18} /> : <Copy size={18} />}
                                                </button>
                                            </div>
                                        </div>
                                        <div className="flex justify-end">
                                            <button
                                                onClick={() => { setResetModal(null); setNewPassword(''); }}
                                                className="px-4 py-2 text-sm font-medium text-white bg-indigo-600 rounded-lg hover:bg-indigo-700 transition-colors"
                                            >
                                                Done
                                            </button>
                                        </div>
                                    </>
                                )}
                            </div>
                        </div>
                    )}

                    {/* Change Role Modal */}
                    {editModal && (
                        <div className="fixed inset-0 bg-black/50 backdrop-blur-sm z-50 flex items-center justify-center p-4" onClick={() => setEditModal(null)}>
                            <div className="bg-white rounded-2xl shadow-2xl max-w-md w-full p-6" onClick={(e) => e.stopPropagation()}>
                                <div className="flex items-center justify-between mb-5">
                                    <div className="flex items-center gap-3">
                                        <div className="p-3 rounded-full bg-indigo-100">
                                            <Shield size={24} className="text-indigo-600" />
                                        </div>
                                        <div>
                                            <h3 className="text-lg font-bold text-gray-900">Change Role</h3>
                                            <p className="text-sm text-gray-500">{editModal.username}</p>
                                        </div>
                                    </div>
                                    <button onClick={() => setEditModal(null)} className="p-1 hover:bg-gray-100 rounded-lg">
                                        <X size={20} className="text-gray-400" />
                                    </button>
                                </div>

                                <div className="space-y-2 mb-6">
                                    {[
                                        { value: 'user', label: 'Regular User', desc: 'Can access public site only', icon: UserIcon, color: 'gray' },
                                        { value: 'staff', label: 'Staff', desc: 'Can access admin panel', icon: ShieldCheck, color: 'blue' },
                                        { value: 'superuser', label: 'Superuser', desc: 'Full access + user management', icon: Crown, color: 'amber' },
                                    ].map((opt) => {
                                        const Icon = opt.icon;
                                        const isSelected = editRole === opt.value;
                                        return (
                                            <button
                                                key={opt.value}
                                                onClick={() => setEditRole(opt.value)}
                                                className={`w-full flex items-center gap-3 p-3.5 rounded-xl border-2 transition-all text-left ${isSelected
                                                    ? `border-${opt.color === 'amber' ? 'amber' : opt.color === 'blue' ? 'blue' : 'gray'}-400 bg-${opt.color === 'amber' ? 'amber' : opt.color === 'blue' ? 'blue' : 'gray'}-50`
                                                    : 'border-gray-100 hover:border-gray-200 hover:bg-gray-50'
                                                    }`}
                                            >
                                                <div className={`p-2 rounded-lg ${opt.color === 'amber' ? 'bg-amber-100' : opt.color === 'blue' ? 'bg-blue-100' : 'bg-gray-100'
                                                    }`}>
                                                    <Icon size={18} className={
                                                        opt.color === 'amber' ? 'text-amber-600' : opt.color === 'blue' ? 'text-blue-600' : 'text-gray-500'
                                                    } />
                                                </div>
                                                <div className="flex-1">
                                                    <div className="font-semibold text-gray-900 text-sm">{opt.label}</div>
                                                    <div className="text-xs text-gray-500">{opt.desc}</div>
                                                </div>
                                                {isSelected && (
                                                    <div className="w-5 h-5 rounded-full bg-indigo-600 flex items-center justify-center">
                                                        <Check size={12} className="text-white" />
                                                    </div>
                                                )}
                                            </button>
                                        );
                                    })}
                                </div>

                                <div className="flex gap-3 justify-end">
                                    <button
                                        onClick={() => setEditModal(null)}
                                        className="px-4 py-2 text-sm font-medium text-gray-700 bg-gray-100 rounded-lg hover:bg-gray-200 transition-colors"
                                    >
                                        Cancel
                                    </button>
                                    <button
                                        onClick={changeRole}
                                        disabled={editRole === editModal.role.toLowerCase() || actionLoading === editModal.id}
                                        className="px-4 py-2 text-sm font-medium text-white bg-indigo-600 rounded-lg hover:bg-indigo-700 transition-colors disabled:opacity-50 flex items-center gap-2"
                                    >
                                        {actionLoading === editModal.id && <Loader2 size={14} className="animate-spin" />}
                                        Save Role
                                    </button>
                                </div>
                            </div>
                        </div>
                    )}

                    {/* Create User Modal */}
                    {createModal && (
                        <div className="fixed inset-0 bg-black/50 backdrop-blur-sm z-50 flex items-center justify-center p-4" onClick={() => setCreateModal(false)}>
                            <div className="bg-white rounded-2xl shadow-2xl max-w-lg w-full p-6" onClick={(e) => e.stopPropagation()}>
                                <div className="flex items-center justify-between mb-5">
                                    <h3 className="text-lg font-bold text-gray-900">Create New User</h3>
                                    <button onClick={() => setCreateModal(false)} className="p-1.5 hover:bg-gray-100 rounded-lg transition-colors">
                                        <X size={18} className="text-gray-400" />
                                    </button>
                                </div>

                                {createError && (
                                    <div className="mb-4 p-3 bg-red-50 border border-red-200 rounded-lg text-sm text-red-700 flex items-center gap-2">
                                        <AlertTriangle size={16} />
                                        {createError}
                                    </div>
                                )}

                                <div className="space-y-4">
                                    <div className="grid grid-cols-2 gap-4">
                                        <div>
                                            <label className="block text-sm font-medium text-gray-700 mb-1">Username *</label>
                                            <input
                                                type="text"
                                                value={createForm.username}
                                                onChange={(e) => setCreateForm({ ...createForm, username: e.target.value })}
                                                className="w-full px-3 py-2 border border-gray-200 rounded-lg text-sm text-gray-900 focus:ring-2 focus:ring-indigo-500 focus:border-transparent outline-none"
                                                placeholder="johndoe"
                                                autoComplete="off"
                                            />
                                        </div>
                                        <div>
                                            <label className="block text-sm font-medium text-gray-700 mb-1">Email</label>
                                            <input
                                                type="email"
                                                value={createForm.email}
                                                onChange={(e) => setCreateForm({ ...createForm, email: e.target.value })}
                                                className="w-full px-3 py-2 border border-gray-200 rounded-lg text-sm text-gray-900 focus:ring-2 focus:ring-indigo-500 focus:border-transparent outline-none"
                                                placeholder="john@example.com"
                                                autoComplete="off"
                                            />
                                        </div>
                                    </div>

                                    <div className="grid grid-cols-2 gap-4">
                                        <div>
                                            <label className="block text-sm font-medium text-gray-700 mb-1">First Name</label>
                                            <input
                                                type="text"
                                                value={createForm.first_name}
                                                onChange={(e) => setCreateForm({ ...createForm, first_name: e.target.value })}
                                                className="w-full px-3 py-2 border border-gray-200 rounded-lg text-sm text-gray-900 focus:ring-2 focus:ring-indigo-500 focus:border-transparent outline-none"
                                                placeholder="John"
                                            />
                                        </div>
                                        <div>
                                            <label className="block text-sm font-medium text-gray-700 mb-1">Last Name</label>
                                            <input
                                                type="text"
                                                value={createForm.last_name}
                                                onChange={(e) => setCreateForm({ ...createForm, last_name: e.target.value })}
                                                className="w-full px-3 py-2 border border-gray-200 rounded-lg text-sm text-gray-900 focus:ring-2 focus:ring-indigo-500 focus:border-transparent outline-none"
                                                placeholder="Doe"
                                            />
                                        </div>
                                    </div>

                                    <div>
                                        <label className="block text-sm font-medium text-gray-700 mb-1">Password *</label>
                                        <div className="relative">
                                            <input
                                                type={showCreatePassword ? 'text' : 'password'}
                                                value={createForm.password}
                                                onChange={(e) => setCreateForm({ ...createForm, password: e.target.value })}
                                                className="w-full px-3 py-2 pr-10 border border-gray-200 rounded-lg text-sm text-gray-900 focus:ring-2 focus:ring-indigo-500 focus:border-transparent outline-none"
                                                placeholder="Minimum 8 characters"
                                                autoComplete="new-password"
                                            />
                                            <button
                                                type="button"
                                                onClick={() => setShowCreatePassword(!showCreatePassword)}
                                                className="absolute right-2.5 top-1/2 -translate-y-1/2 text-gray-400 hover:text-gray-600"
                                            >
                                                {showCreatePassword ? <EyeOff size={16} /> : <Eye size={16} />}
                                            </button>
                                        </div>
                                    </div>

                                    <div>
                                        <label className="block text-sm font-medium text-gray-700 mb-2">Role</label>
                                        <div className="grid grid-cols-3 gap-2">
                                            {[
                                                { value: 'user', label: 'User', icon: UserIcon, color: 'gray' },
                                                { value: 'staff', label: 'Staff', icon: Shield, color: 'blue' },
                                                { value: 'superuser', label: 'Superuser', icon: Crown, color: 'amber' },
                                            ].map((r) => {
                                                const RIcon = r.icon;
                                                return (
                                                    <button
                                                        key={r.value}
                                                        type="button"
                                                        onClick={() => setCreateForm({ ...createForm, role: r.value })}
                                                        className={`flex flex-col items-center gap-1.5 p-3 rounded-xl border-2 transition-all text-sm font-medium ${createForm.role === r.value
                                                            ? 'border-indigo-500 bg-indigo-50 text-indigo-700'
                                                            : 'border-gray-200 hover:border-gray-300 text-gray-600'
                                                            }`}
                                                    >
                                                        <RIcon size={18} />
                                                        {r.label}
                                                    </button>
                                                );
                                            })}
                                        </div>
                                    </div>
                                </div>

                                <div className="flex gap-3 justify-end mt-6">
                                    <button
                                        onClick={() => setCreateModal(false)}
                                        className="px-4 py-2 text-sm font-medium text-gray-700 bg-gray-100 rounded-lg hover:bg-gray-200 transition-colors"
                                    >
                                        Cancel
                                    </button>
                                    <button
                                        onClick={createUser}
                                        disabled={!createForm.username || !createForm.password || createLoading}
                                        className="px-5 py-2 text-sm font-semibold text-white bg-gradient-to-r from-indigo-600 to-purple-600 rounded-lg hover:from-indigo-700 hover:to-purple-700 transition-all disabled:opacity-50 flex items-center gap-2"
                                    >
                                        {createLoading && <Loader2 size={14} className="animate-spin" />}
                                        Create User
                                    </button>
                                </div>
                            </div>
                        </div>
                    )}
                </>
            )}
        </div>
    );
}
