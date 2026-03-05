import React from 'react';
import { Crown, ShieldCheck, User as UserIcon } from 'lucide-react';

interface UserRoleBadgeProps {
    role: 'Superuser' | 'Staff' | 'User' | string;
}

export function UserRoleBadge({ role }: UserRoleBadgeProps) {
    if (role === 'Superuser') {
        return (
            <span className="inline-flex items-center gap-1.5 px-2.5 py-1 rounded-full text-xs font-medium bg-amber-100 text-amber-800 border border-amber-200">
                <Crown size={12} className="text-amber-600" />
                Superuser
            </span>
        );
    }

    if (role === 'Staff') {
        return (
            <span className="inline-flex items-center gap-1.5 px-2.5 py-1 rounded-full text-xs font-medium bg-indigo-100 text-indigo-700 border border-indigo-200">
                <ShieldCheck size={12} className="text-indigo-500" />
                Staff
            </span>
        );
    }

    return (
        <span className="inline-flex items-center gap-1.5 px-2.5 py-1 rounded-full text-xs font-medium bg-gray-100 text-gray-600 border border-gray-200">
            <UserIcon size={12} className="text-gray-400" />
            User
        </span>
    );
}
