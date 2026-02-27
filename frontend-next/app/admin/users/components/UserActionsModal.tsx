import React, { useState } from 'react';
import { FormField } from '../../components/forms/FormCard';
import {
    AlertTriangle, KeyRound, Copy, Check, ShieldAlert,
    Trash2, UserCog, UserPlus, X, Loader2
} from 'lucide-react';

interface UserData {
    id: number;
    username: string;
    email: string;
    first_name: string;
    last_name: string;
    role: 'Superuser' | 'Staff' | 'User';
}

interface CommonModalProps {
    isOpen: boolean;
    onClose: () => void;
    title: string;
    icon: React.ReactNode;
    children: React.ReactNode;
    actions: React.ReactNode;
}

function BaseModal({ isOpen, onClose, title, icon, children, actions }: CommonModalProps) {
    if (!isOpen) return null;

    return (
        <div className="fixed inset-0 z-50 flex items-center justify-center p-4">
            <div
                className="absolute inset-0 bg-gray-900/40 backdrop-blur-sm transition-opacity"
                onClick={onClose}
            />
            <div className="relative bg-white dark:bg-gray-800 rounded-2xl w-full max-w-md overflow-hidden shadow-2xl animate-in fade-in zoom-in-95 duration-200">
                <div className="flex items-center justify-between p-6 border-b border-gray-100 dark:border-gray-700 bg-gray-50/50 dark:bg-gray-800/50">
                    <div className="flex items-center gap-3">
                        <div className="p-2 bg-white dark:bg-gray-700 rounded-lg shadow-sm">
                            {icon}
                        </div>
                        <h3 className="text-lg font-semibold text-gray-900 dark:text-white">
                            {title}
                        </h3>
                    </div>
                    <button
                        onClick={onClose}
                        className="text-gray-400 hover:text-gray-500 dark:hover:text-gray-300 p-2 hover:bg-gray-100 dark:hover:bg-gray-700 rounded-xl transition-colors"
                    >
                        <X size={20} />
                    </button>
                </div>

                <div className="p-6">
                    {children}
                </div>

                <div className="p-6 pt-0 flex gap-3">
                    {actions}
                </div>
            </div>
        </div>
    );
}

// -------------------------------------------------------------
// Individual Specific Modals
// -------------------------------------------------------------

export function DeleteUserModal({ isOpen, onClose, onConfirm, user, isSaving }: any) {
    return (
        <BaseModal
            isOpen={isOpen}
            onClose={onClose}
            title="Delete User"
            icon={<Trash2 className="text-red-500" size={24} />}
            actions={
                <>
                    <button
                        onClick={onClose}
                        className="flex-1 px-4 py-2 text-gray-700 dark:text-gray-200 bg-gray-100 dark:bg-gray-700 hover:bg-gray-200 dark:hover:bg-gray-600 rounded-xl transition-colors font-medium"
                    >
                        Cancel
                    </button>
                    <button
                        onClick={onConfirm}
                        disabled={isSaving}
                        className="flex-1 flex items-center justify-center gap-2 px-4 py-2 bg-red-600 hover:bg-red-700 text-white rounded-xl transition-colors disabled:opacity-50 font-medium"
                    >
                        {isSaving ? <Loader2 size={18} className="animate-spin" /> : <Trash2 size={18} />}
                        Delete User
                    </button>
                </>
            }
        >
            <div className="space-y-4">
                <div className="p-4 bg-red-50 dark:bg-red-900/20 rounded-xl flex gap-3 text-red-600 dark:text-red-400">
                    <AlertTriangle className="shrink-0" size={20} />
                    <p className="text-sm">
                        This action cannot be undone. This will permanently delete the user account entirely.
                    </p>
                </div>
                <p className="text-gray-600 dark:text-gray-300">
                    Are you sure you want to delete <strong className="text-gray-900 dark:text-white">{user?.username}</strong>?
                </p>
            </div>
        </BaseModal>
    );
}

export function RoleModal({ isOpen, onClose, onConfirm, user, isSaving }: any) {
    const [selectedRole, setSelectedRole] = useState(user?.role || 'User');

    // Update state if user prop changes
    React.useEffect(() => {
        if (user) setSelectedRole(user.role);
    }, [user]);

    return (
        <BaseModal
            isOpen={isOpen}
            onClose={onClose}
            title="Manage Role"
            icon={<UserCog className="text-indigo-500" size={24} />}
            actions={
                <>
                    <button
                        onClick={onClose}
                        className="flex-1 px-4 py-2 text-gray-700 dark:text-gray-200 bg-gray-100 dark:bg-gray-700 hover:bg-gray-200 dark:hover:bg-gray-600 rounded-xl transition-colors font-medium"
                    >
                        Cancel
                    </button>
                    <button
                        onClick={() => onConfirm(selectedRole)}
                        disabled={isSaving || selectedRole === user?.role}
                        className="flex-1 flex items-center justify-center gap-2 px-4 py-2 bg-indigo-600 hover:bg-indigo-700 text-white rounded-xl transition-colors disabled:opacity-50 font-medium"
                    >
                        {isSaving ? <Loader2 size={18} className="animate-spin" /> : 'Save Changes'}
                    </button>
                </>
            }
        >
            <div className="space-y-4">
                <p className="text-gray-600 dark:text-gray-300">
                    Update role for <strong className="text-gray-900 dark:text-white">{user?.username}</strong>
                </p>

                <div className="space-y-3">
                    {['User', 'Staff', 'Superuser'].map((role) => (
                        <label
                            key={role}
                            className={`flex items-center p-4 border rounded-xl cursor-pointer transition-colors ${selectedRole === role
                                    ? 'border-indigo-500 bg-indigo-50 dark:bg-indigo-900/20'
                                    : 'border-gray-200 dark:border-gray-700 bg-white dark:bg-gray-800 hover:bg-gray-50 dark:hover:bg-gray-700/50'
                                }`}
                        >
                            <input
                                type="radio"
                                name="role"
                                value={role}
                                checked={selectedRole === role}
                                onChange={(e) => setSelectedRole(e.target.value)}
                                className="w-4 h-4 text-indigo-600 border-gray-300 focus:ring-indigo-500"
                            />
                            <div className="ml-3">
                                <span className="block text-sm font-medium text-gray-900 dark:text-white">
                                    {role}
                                </span>
                                <span className="block text-xs text-gray-500 dark:text-gray-400 mt-1">
                                    {role === 'Superuser' && 'Full access to all system features and settings'}
                                    {role === 'Staff' && 'Access to admin panel to manage content and moderate'}
                                    {role === 'User' && 'Standard user access, no admin privileges'}
                                </span>
                            </div>
                        </label>
                    ))}
                </div>
            </div>
        </BaseModal>
    );
}

// And so on for the others - Password and Create...
