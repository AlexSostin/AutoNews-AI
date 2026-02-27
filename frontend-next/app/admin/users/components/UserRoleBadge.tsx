import React from 'react';
import { Crown, ShieldCheck, User as UserIcon } from 'lucide-react';

interface UserRoleBadgeProps {
    role: 'Superuser' | 'Staff' | 'User' | string;
}

export function UserRoleBadge({ role }: UserRoleBadgeProps) {
    if (role === 'Superuser') {
        return (
            <span className="inline-flex items-center gap-1.5 px-2.5 py-1 rounded-full text-xs font-medium bg-amber-100 text-amber-800 dark:bg-amber-900/30 dark:text-amber-300 border border-amber-200 dark:border-amber-800">
                <Crown size={12} className="text-amber-600 dark:text-amber-400" />
                Superuser
            </span>
        );
    }

    if (role === 'Staff') {
        return (
            <span className="inline-flex items-center gap-1.5 px-2.5 py-1 rounded-full text-xs font-medium bg-indigo-100 text-indigo-800 dark:bg-indigo-900/30 dark:text-indigo-300 border border-indigo-200 dark:border-indigo-800">
                <ShieldCheck size={12} className="text-indigo-600 dark:text-indigo-400" />
                Staff
            </span>
        );
    }

    return (
        <span className="inline-flex items-center gap-1.5 px-2.5 py-1 rounded-full text-xs font-medium bg-gray-100 text-gray-800 dark:bg-gray-800 dark:text-gray-300 border border-gray-200 dark:border-gray-700">
            <UserIcon size={12} className="text-gray-500 dark:text-gray-400" />
            User
        </span>
    );
}
