'use client';

import { useState, useEffect } from 'react';
import { Fingerprint, Trash2, Plus, Smartphone, CheckCircle, AlertCircle, Loader2 } from 'lucide-react';
import {
    browserSupportsWebAuthn,
    registerPasskey,
    listPasskeys,
    deletePasskey,
    type PasskeyCredential,
} from '@/lib/passkey';
import toast from 'react-hot-toast';

export default function PasskeyManager() {
    const [passkeys, setPasskeys] = useState<PasskeyCredential[]>([]);
    const [isSupported, setIsSupported] = useState(false);
    const [isLoading, setIsLoading] = useState(true);
    const [isRegistering, setIsRegistering] = useState(false);
    const [deviceName, setDeviceName] = useState('');
    const [showNameInput, setShowNameInput] = useState(false);

    useEffect(() => {
        setIsSupported(browserSupportsWebAuthn());
        loadPasskeys();
    }, []);

    async function loadPasskeys() {
        setIsLoading(true);
        try {
            const creds = await listPasskeys();
            setPasskeys(creds);
        } catch {
            // silently fail
        } finally {
            setIsLoading(false);
        }
    }

    async function handleRegister() {
        if (!deviceName.trim()) {
            toast.error('Enter a device name first');
            return;
        }
        setIsRegistering(true);
        try {
            const result = await registerPasskey(deviceName.trim());
            toast.success(`✅ Passkey "${result.device_name}" added!`);
            setDeviceName('');
            setShowNameInput(false);
            await loadPasskeys();
        } catch (err: unknown) {
            const msg = err instanceof Error ? err.message : 'Registration failed';
            // AbortError = user cancelled — don't show error toast
            if (!msg.includes('AbortError') && !msg.includes('NotAllowedError')) {
                toast.error(msg);
            }
        } finally {
            setIsRegistering(false);
        }
    }

    async function handleDelete(pk: number, name: string) {
        if (!confirm(`Remove passkey "${name}"?`)) return;
        try {
            await deletePasskey(pk);
            toast.success(`Passkey "${name}" removed`);
            setPasskeys(prev => prev.filter(p => p.id !== pk));
        } catch {
            toast.error('Failed to remove passkey');
        }
    }

    if (!isSupported) {
        return (
            <div className="flex items-center gap-2 text-amber-600 bg-amber-50 border border-amber-200 rounded-xl px-4 py-3 text-sm">
                <AlertCircle size={16} />
                Your browser doesn&apos;t support passkeys. Use Chrome/Safari on Android or iOS.
            </div>
        );
    }

    return (
        <div className="space-y-4">
            <div className="flex items-center justify-between">
                <div className="flex items-center gap-2">
                    <Fingerprint className="text-indigo-600" size={20} />
                    <h3 className="font-semibold text-gray-900">Passkeys</h3>
                    <span className="text-xs bg-green-100 text-green-700 px-2 py-0.5 rounded-full font-medium">Passwordless</span>
                </div>
                {!showNameInput && (
                    <button
                        onClick={() => setShowNameInput(true)}
                        className="flex items-center gap-1.5 text-sm bg-indigo-600 text-white px-3 py-2 rounded-lg hover:bg-indigo-700 transition-colors font-medium"
                    >
                        <Plus size={15} />
                        Add Passkey
                    </button>
                )}
            </div>

            <p className="text-xs text-gray-500">
                Sign in with Touch ID, Face ID, or fingerprint — no password needed.
            </p>

            {/* Register form */}
            {showNameInput && (
                <div className="bg-indigo-50 border border-indigo-200 rounded-xl p-4 space-y-3">
                    <p className="text-sm font-medium text-indigo-900">Name this device</p>
                    <input
                        type="text"
                        value={deviceName}
                        onChange={e => setDeviceName(e.target.value)}
                        onKeyDown={e => e.key === 'Enter' && handleRegister()}
                        placeholder='e.g. "iPhone 15" or "Pixel 8"'
                        className="w-full px-3 py-2 border border-indigo-300 rounded-lg text-sm focus:ring-2 focus:ring-indigo-500 outline-none bg-white text-gray-900"
                        autoFocus
                    />
                    <div className="flex gap-2">
                        <button
                            onClick={handleRegister}
                            disabled={isRegistering || !deviceName.trim()}
                            className="flex items-center gap-2 bg-indigo-600 text-white px-4 py-2 rounded-lg text-sm font-semibold hover:bg-indigo-700 disabled:opacity-50 disabled:cursor-not-allowed transition-colors"
                        >
                            {isRegistering ? (
                                <><Loader2 size={15} className="animate-spin" /> Registering…</>
                            ) : (
                                <><Fingerprint size={15} /> Scan Fingerprint</>
                            )}
                        </button>
                        <button
                            onClick={() => { setShowNameInput(false); setDeviceName(''); }}
                            className="px-4 py-2 rounded-lg text-sm text-gray-500 hover:text-gray-700 transition-colors"
                        >
                            Cancel
                        </button>
                    </div>
                </div>
            )}

            {/* Passkey list */}
            {isLoading ? (
                <div className="flex items-center gap-2 text-gray-400 text-sm py-2">
                    <Loader2 size={15} className="animate-spin" /> Loading passkeys…
                </div>
            ) : passkeys.length === 0 ? (
                <div className="text-sm text-gray-400 py-2 text-center border border-dashed border-gray-200 rounded-xl">
                    No passkeys yet. Add one to skip the password next time.
                </div>
            ) : (
                <div className="space-y-2">
                    {passkeys.map(pk => (
                        <div key={pk.id} className="flex items-center justify-between bg-white border border-gray-100 rounded-xl px-4 py-3 shadow-sm">
                            <div className="flex items-center gap-3">
                                <div className="bg-indigo-100 p-2 rounded-lg">
                                    <Smartphone className="text-indigo-600" size={16} />
                                </div>
                                <div>
                                    <p className="text-sm font-semibold text-gray-900">{pk.device_name}</p>
                                    <p className="text-xs text-gray-400">
                                        Added {new Date(pk.created_at).toLocaleDateString()}
                                        {pk.last_used && ` · Last used ${new Date(pk.last_used).toLocaleDateString()}`}
                                    </p>
                                </div>
                            </div>
                            <div className="flex items-center gap-2">
                                <CheckCircle className="text-green-500" size={16} />
                                <button
                                    onClick={() => handleDelete(pk.id, pk.device_name)}
                                    className="p-1.5 text-gray-400 hover:text-red-500 transition-colors rounded-lg hover:bg-red-50"
                                    title="Remove passkey"
                                >
                                    <Trash2 size={15} />
                                </button>
                            </div>
                        </div>
                    ))}
                </div>
            )}
        </div>
    );
}
