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
import { UserRoleBadge } from './components/UserRoleBadge';
import { DeleteUserModal, RoleModal } from './components/UserActionsModal';
import { PageHeader } from '../components/ui/PageHeader';
import { UserTable } from './components/UserTable';
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
    const [selectedUser, setSelectedUser] = useState<UserData | null>(null);
    const [deleteModal, setDeleteModal] = useState<UserData | null>(null);
    const [showDeleteModal, setShowDeleteModal] = useState(false);

    const [resetModal, setResetModal] = useState<UserData | null>(null);
    const [showPasswordModal, setShowPasswordModal] = useState(false);
    const [newPassword, setNewPassword] = useState('');
    const [copied, setCopied] = useState(false);
    const [copiedId, setCopiedId] = useState<number | null>(null);

    const [editModal, setEditModal] = useState<UserData | null>(null);
    const [showRoleModal, setShowRoleModal] = useState(false);
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
                    <UserTable
                        users={users}
                        onToggleActive={toggleActive}
                        onChangeRole={(user: any) => { setEditModal(user); setEditRole(user.role.toLowerCase()); }}
                        onResetPassword={(user: any) => { setResetModal(user); setNewPassword(''); setCopied(false); }}
                        onDeleteUser={(user: any) => setDeleteModal(user)}
                        onCopyPassword={copyPassword}
                        formatDate={formatDate}
                        copiedId={copiedId}
                        currentUser={currentUserId}
                    />

                    {/* Pagination */}

                    {/* Delete User Modal */}
                    <DeleteUserModal
                        isOpen={deleteModal !== null}
                        onClose={() => setDeleteModal(null)}
                        onConfirm={deleteUser}
                        user={deleteModal}
                        isSaving={actionLoading === deleteModal?.id}
                    />

                    {/* Role Management Modal */}
                    <RoleModal
                        isOpen={editModal !== null}
                        onClose={() => setEditModal(null)}
                        onConfirm={changeRole}
                        user={editModal}
                        isSaving={actionLoading === editModal?.id}
                    />

                </>
            )
            }
        </div >
    );
}