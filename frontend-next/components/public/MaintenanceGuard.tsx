'use client';

import { useEffect, useState } from 'react';
import { getToken } from '@/lib/auth';
import { getApiUrl } from '@/lib/config';

interface MaintenanceGuardProps {
    maintenanceMode: boolean;
    maintenanceMessage?: string;
    children: React.ReactNode;
    fallback: React.ReactNode;
}

/**
 * Client-side maintenance mode guard.
 * Shows maintenance page to non-admin users when maintenance_mode is enabled.
 * Admin check happens client-side so the page itself can be cached via ISR.
 */
export default function MaintenanceGuard({
    maintenanceMode,
    maintenanceMessage,
    children,
    fallback,
}: MaintenanceGuardProps) {
    const [isAdmin, setIsAdmin] = useState(false);
    const [checked, setChecked] = useState(!maintenanceMode); // if not maintenance, skip check

    useEffect(() => {
        if (!maintenanceMode) {
            setChecked(true);
            return;
        }

        // Check admin status client-side
        const token = getToken();
        if (!token) {
            setChecked(true);
            return;
        }
        fetch(`${getApiUrl()}/users/me/`, {
            headers: { 'Authorization': `Bearer ${token}` },
        })
            .then(res => res.ok ? res.json() : null)
            .then(user => {
                if (user && (user.is_staff || user.is_superuser)) {
                    setIsAdmin(true);
                }
                setChecked(true);
            })
            .catch(() => setChecked(true));
    }, [maintenanceMode]);

    // Still checking admin status — show nothing briefly
    if (!checked) return null;

    // Maintenance mode ON and user is NOT admin → show maintenance page
    if (maintenanceMode && !isAdmin) {
        return <>{fallback}</>;
    }

    return <>{children}</>;
}
