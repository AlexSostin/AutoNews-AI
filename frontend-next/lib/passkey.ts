/**
 * WebAuthn / Passkey helpers.
 * Uses @simplewebauthn/browser for credential creation & assertion.
 *
 * API endpoints (all at /api/v1/):
 *   POST  auth/passkey/register/begin/     → registration options
 *   POST  auth/passkey/register/complete/  → verify & save
 *   GET   auth/passkey/authenticate/       → authentication options
 *   POST  auth/passkey/authenticate/       → verify & return JWT
 *   GET   auth/passkey/credentials/        → list credentials
 *   DELETE auth/passkey/credentials/<pk>/  → delete credential
 */

import {
    startRegistration,
    startAuthentication,
    browserSupportsWebAuthn,
} from '@simplewebauthn/browser';
import { getApiUrl } from './api';

export { browserSupportsWebAuthn };

const API = () => getApiUrl();

// ─── Token helpers (same as auth.ts) ──────────────────────────────────────────

function _setCookieAndStorage(access: string, refresh: string) {
    const isSecure = window.location.protocol === 'https:';
    const secureFlag = isSecure ? '; Secure' : '';
    document.cookie = `access_token=${access}; path=/; max-age=${7 * 86400}; SameSite=Lax${secureFlag}`;
    document.cookie = `refresh_token=${refresh}; path=/; max-age=${30 * 86400}; SameSite=Lax${secureFlag}`;
    localStorage.setItem('access_token', access);
    localStorage.setItem('refresh_token', refresh);
}

// ─── Register (add a passkey to current account) ──────────────────────────────

export async function registerPasskey(deviceName = 'My Passkey'): Promise<{ device_name: string; created_at: string }> {
    const accessToken = localStorage.getItem('access_token');
    if (!accessToken) throw new Error('Not authenticated');

    // Step 1: get registration options from backend
    const beginRes = await fetch(`${API()}/auth/passkey/register/begin/`, {
        method: 'POST',
        headers: {
            'Authorization': `Bearer ${accessToken}`,
            'Content-Type': 'application/json',
            'X-CSRFToken': _getCSRF(),
        },
        credentials: 'include',
    });
    if (!beginRes.ok) throw new Error('Failed to start registration');
    const options = await beginRes.json();

    // Step 2: browser calls Touch ID / Face ID / platform authenticator
    const credential = await startRegistration({ optionsJSON: options });

    // Step 3: send response to backend for verification
    const completeRes = await fetch(`${API()}/auth/passkey/register/complete/`, {
        method: 'POST',
        headers: {
            'Authorization': `Bearer ${accessToken}`,
            'Content-Type': 'application/json',
            'X-CSRFToken': _getCSRF(),
        },
        credentials: 'include',
        body: JSON.stringify({ ...credential, device_name: deviceName }),
    });

    if (!completeRes.ok) {
        const err = await completeRes.json().catch(() => ({}));
        throw new Error(err.detail || 'Registration failed');
    }

    return completeRes.json();
}

// ─── Login with passkey (no password) ─────────────────────────────────────────

export async function loginWithPasskey(): Promise<{ access: string; refresh: string }> {
    // Step 1: get challenge from backend
    const authOptionsRes = await fetch(`${API()}/auth/passkey/authenticate/`, {
        method: 'GET',
        credentials: 'include',
        headers: { 'X-CSRFToken': _getCSRF() },
    });
    if (!authOptionsRes.ok) throw new Error('Could not start passkey login');
    const options = await authOptionsRes.json();

    // Step 2: browser asks for biometrics
    const assertion = await startAuthentication({ optionsJSON: options });

    // Step 3: verify with backend → get JWT
    const verifyRes = await fetch(`${API()}/auth/passkey/authenticate/`, {
        method: 'POST',
        credentials: 'include',
        headers: {
            'Content-Type': 'application/json',
            'X-CSRFToken': _getCSRF(),
        },
        body: JSON.stringify(assertion),
    });

    if (!verifyRes.ok) {
        const err = await verifyRes.json().catch(() => ({}));
        throw new Error(err.detail || 'Passkey authentication failed');
    }

    const tokens = await verifyRes.json() as { access: string; refresh: string };
    _setCookieAndStorage(tokens.access, tokens.refresh);
    return tokens;
}

// ─── List passkeys ─────────────────────────────────────────────────────────────

export interface PasskeyCredential {
    id: number;
    device_name: string;
    created_at: string;
    last_used: string | null;
    transports: string[];
}

export async function listPasskeys(): Promise<PasskeyCredential[]> {
    const accessToken = localStorage.getItem('access_token');
    if (!accessToken) return [];

    const res = await fetch(`${API()}/auth/passkey/credentials/`, {
        headers: { 'Authorization': `Bearer ${accessToken}` },
        credentials: 'include',
    });
    if (!res.ok) return [];
    return res.json();
}

// ─── Delete passkey ────────────────────────────────────────────────────────────

export async function deletePasskey(pk: number): Promise<void> {
    const accessToken = localStorage.getItem('access_token');
    await fetch(`${API()}/auth/passkey/credentials/${pk}/`, {
        method: 'DELETE',
        headers: {
            'Authorization': `Bearer ${accessToken}`,
            'X-CSRFToken': _getCSRF(),
        },
        credentials: 'include',
    });
}

// ─── CSRF helper ───────────────────────────────────────────────────────────────

function _getCSRF(): string {
    if (typeof document === 'undefined') return '';
    const cookie = document.cookie.split(';').find(c => c.trim().startsWith('csrftoken='));
    return cookie ? cookie.split('=')[1].trim() : '';
}
