'use client';

import { useState, useEffect } from 'react';
import {
  User,
  Mail,
  Lock,
  Save,
  Loader2,
  Eye,
  EyeOff,
  Shield,
  Check,
  Smartphone,
  ShieldCheck,
  ShieldX,
  Copy,
  AlertTriangle
} from 'lucide-react';
import { authenticatedFetch } from '@/lib/authenticatedFetch';
import dynamic from 'next/dynamic';

const PasskeyManager = dynamic(() => import('@/components/admin/PasskeyManager'), { ssr: false });

interface UserProfile {
  username: string;
  email: string;
  first_name: string;
  last_name: string;
}

type TwoFAStep = 'idle' | 'setup' | 'confirm' | 'backup' | 'disable';

export default function AccountSettingsPage() {
  const [profile, setProfile] = useState<UserProfile>({
    username: '',
    email: '',
    first_name: '',
    last_name: ''
  });
  const [passwords, setPasswords] = useState({
    current_password: '',
    new_password: '',
    confirm_password: ''
  });

  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);
  const [savingPassword, setSavingPassword] = useState(false);
  const [showCurrentPassword, setShowCurrentPassword] = useState(false);
  const [showNewPassword, setShowNewPassword] = useState(false);
  const [message, setMessage] = useState<{ type: 'success' | 'error'; text: string } | null>(null);

  // 2FA state
  const [twoFAEnabled, setTwoFAEnabled] = useState(false);
  const [twoFAStep, setTwoFAStep] = useState<TwoFAStep>('idle');
  const [twoFALoading, setTwoFALoading] = useState(false);
  const [qrCode, setQrCode] = useState<string>('');
  const [totpSecret, setTotpSecret] = useState<string>('');
  const [totpCode, setTotpCode] = useState('');
  const [disableCode, setDisableCode] = useState('');
  const [backupCodes, setBackupCodes] = useState<string[]>([]);
  const [twoFAMessage, setTwoFAMessage] = useState<{ type: 'success' | 'error'; text: string } | null>(null);
  const [copiedBackup, setCopiedBackup] = useState(false);

  useEffect(() => {
    fetchProfile();
    fetchTwoFAStatus();
  }, []);

  const fetchTwoFAStatus = async () => {
    try {
      const res = await authenticatedFetch('/auth/2fa/status/');
      if (res.ok) {
        const data = await res.json();
        setTwoFAEnabled(data.enabled);
      }
    } catch { /* silent */ }
  };

  const handleSetup2FA = async () => {
    setTwoFALoading(true);
    setTwoFAMessage(null);
    try {
      const res = await authenticatedFetch('/auth/2fa/setup/', { method: 'POST' });
      const data = await res.json();
      if (res.ok) {
        setQrCode(data.qr_code);
        setTotpSecret(data.secret);
        setTwoFAStep('setup');
      } else {
        setTwoFAMessage({ type: 'error', text: data.detail || 'Failed to generate QR code' });
      }
    } catch {
      setTwoFAMessage({ type: 'error', text: 'An error occurred' });
    } finally {
      setTwoFALoading(false);
    }
  };

  const handleConfirm2FA = async () => {
    if (totpCode.length !== 6) return;
    setTwoFALoading(true);
    setTwoFAMessage(null);
    try {
      const res = await authenticatedFetch('/auth/2fa/confirm/', {
        method: 'POST',
        body: JSON.stringify({ code: totpCode }),
      });
      const data = await res.json();
      if (res.ok) {
        setBackupCodes(data.backup_codes);
        setTwoFAStep('backup');
        setTwoFAEnabled(true);
        setTotpCode('');
      } else {
        setTwoFAMessage({ type: 'error', text: data.detail || 'Invalid code' });
      }
    } catch {
      setTwoFAMessage({ type: 'error', text: 'An error occurred' });
    } finally {
      setTwoFALoading(false);
    }
  };

  const handleDisable2FA = async () => {
    if (!disableCode) return;
    setTwoFALoading(true);
    setTwoFAMessage(null);
    try {
      const res = await authenticatedFetch('/auth/2fa/disable/', {
        method: 'POST',
        body: JSON.stringify({ code: disableCode }),
      });
      const data = await res.json();
      if (res.ok) {
        setTwoFAEnabled(false);
        setTwoFAStep('idle');
        setDisableCode('');
        setTwoFAMessage({ type: 'success', text: '2FA disabled successfully.' });
      } else {
        setTwoFAMessage({ type: 'error', text: data.detail || 'Invalid code' });
      }
    } catch {
      setTwoFAMessage({ type: 'error', text: 'An error occurred' });
    } finally {
      setTwoFALoading(false);
    }
  };

  const copyBackupCodes = () => {
    navigator.clipboard.writeText(backupCodes.join('\n'));
    setCopiedBackup(true);
    setTimeout(() => setCopiedBackup(false), 2000);
  };


  const fetchProfile = async () => {
    try {
      const response = await authenticatedFetch('/auth/user/');

      if (response.ok) {
        const data = await response.json();
        setProfile({
          username: data.username || '',
          email: data.email || '',
          first_name: data.first_name || '',
          last_name: data.last_name || ''
        });
      }
    } catch (error) {
      console.error('Failed to fetch profile:', error);
    } finally {
      setLoading(false);
    }
  };

  const handleProfileUpdate = async (e: React.FormEvent) => {
    e.preventDefault();
    setSaving(true);
    setMessage(null);

    try {
      const response = await authenticatedFetch('/auth/user/', {
        method: 'PATCH',
        body: JSON.stringify({
          first_name: profile.first_name,
          last_name: profile.last_name,
        })
      });

      if (response.ok) {
        setMessage({ type: 'success', text: 'Profile updated successfully!' });
      } else {
        const data = await response.json();
        setMessage({ type: 'error', text: data.detail || 'Failed to update profile' });
      }
    } catch {
      setMessage({ type: 'error', text: 'An error occurred' });
    } finally {
      setSaving(false);
    }
  };

  const handlePasswordChange = async (e: React.FormEvent) => {
    e.preventDefault();

    if (passwords.new_password !== passwords.confirm_password) {
      setMessage({ type: 'error', text: 'New passwords do not match' });
      return;
    }

    if (passwords.new_password.length < 8) {
      setMessage({ type: 'error', text: 'Password must be at least 8 characters' });
      return;
    }

    setSavingPassword(true);
    setMessage(null);

    try {
      const response = await authenticatedFetch('/auth/password/change/', {
        method: 'POST',
        body: JSON.stringify({
          old_password: passwords.current_password,
          new_password1: passwords.new_password,
          new_password2: passwords.confirm_password
        })
      });

      if (response.ok) {
        setMessage({ type: 'success', text: 'Password changed successfully!' });
        setPasswords({ current_password: '', new_password: '', confirm_password: '' });
      } else {
        const data = await response.json();
        const errorMsg = data.old_password?.[0] || data.new_password1?.[0] || data.detail || 'Failed to change password';
        setMessage({ type: 'error', text: errorMsg });
      }
    } catch {
      setMessage({ type: 'error', text: 'An error occurred' });
    } finally {
      setSavingPassword(false);
    }
  };

  if (loading) {
    return (
      <div className="flex items-center justify-center min-h-[60vh]">
        <Loader2 className="animate-spin text-purple-600" size={48} />
      </div>
    );
  }

  return (
    <div className="space-y-6 max-w-4xl">
      <h1 className="text-2xl sm:text-3xl font-black text-gray-900">Account Settings</h1>

      {message && (
        <div className={`p-4 rounded-lg flex items-center gap-2 ${message.type === 'success'
          ? 'bg-green-50 text-green-800 border border-green-200'
          : 'bg-red-50 text-red-800 border border-red-200'
          }`}>
          {message.type === 'success' ? <Check size={20} /> : <Shield size={20} />}
          {message.text}
        </div>
      )}

      {/* Profile Section */}
      <div className="bg-white rounded-xl shadow-md p-6">
        <div className="flex items-center gap-3 mb-6">
          <div className="bg-purple-100 p-3 rounded-lg">
            <User className="text-purple-600" size={24} />
          </div>
          <div>
            <h2 className="text-xl font-bold text-gray-900">Profile Information</h2>
            <p className="text-gray-500 text-sm">Update your personal information</p>
          </div>
        </div>

        <form onSubmit={handleProfileUpdate} className="space-y-4">
          <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1">
                Username
              </label>
              <input
                type="text"
                value={profile.username}
                disabled
                className="w-full px-4 py-2 border border-gray-300 rounded-lg bg-gray-100 text-gray-500 cursor-not-allowed"
              />
              <p className="text-xs text-gray-400 mt-1">Username cannot be changed</p>
            </div>

            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1">
                Email Address
              </label>
              <div className="relative">
                <Mail className="absolute left-3 top-1/2 -translate-y-1/2 text-gray-400" size={18} />
                <input
                  type="email"
                  value={profile.email}
                  disabled
                  className="w-full pl-10 pr-4 py-2 border border-gray-300 rounded-lg bg-gray-100 text-gray-500 cursor-not-allowed"
                />
              </div>
              <p className="text-xs text-gray-400 mt-1">Email changes require verification — use Profile page</p>
            </div>

            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1">
                First Name
              </label>
              <input
                type="text"
                value={profile.first_name}
                onChange={(e) => setProfile({ ...profile, first_name: e.target.value })}
                className="w-full px-4 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-purple-500 focus:border-transparent text-gray-900"
                placeholder="Enter first name"
              />
            </div>

            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1">
                Last Name
              </label>
              <input
                type="text"
                value={profile.last_name}
                onChange={(e) => setProfile({ ...profile, last_name: e.target.value })}
                className="w-full px-4 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-purple-500 focus:border-transparent text-gray-900"
                placeholder="Enter last name"
              />
            </div>
          </div>

          <div className="flex justify-end pt-4">
            <button
              type="submit"
              disabled={saving}
              className="flex items-center gap-2 px-6 py-2 bg-purple-600 text-white rounded-lg hover:bg-purple-700 transition-colors disabled:opacity-50"
            >
              {saving ? <Loader2 className="animate-spin" size={18} /> : <Save size={18} />}
              Save Changes
            </button>
          </div>
        </form>
      </div>

      {/* Password Section */}
      <div className="bg-white rounded-xl shadow-md p-6">
        <div className="flex items-center gap-3 mb-6">
          <div className="bg-orange-100 p-3 rounded-lg">
            <Lock className="text-orange-600" size={24} />
          </div>
          <div>
            <h2 className="text-xl font-bold text-gray-900">Change Password</h2>
            <p className="text-gray-500 text-sm">Update your password regularly for security</p>
          </div>
        </div>

        <form onSubmit={handlePasswordChange} className="space-y-4">
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-1">
              Current Password
            </label>
            <div className="relative">
              <Lock className="absolute left-3 top-1/2 -translate-y-1/2 text-gray-400" size={18} />
              <input
                type={showCurrentPassword ? 'text' : 'password'}
                value={passwords.current_password}
                onChange={(e) => setPasswords({ ...passwords, current_password: e.target.value })}
                className="w-full pl-10 pr-12 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-purple-500 focus:border-transparent text-gray-900"
                placeholder="Enter current password"
              />
              <button
                type="button"
                onClick={() => setShowCurrentPassword(!showCurrentPassword)}
                className="absolute inset-y-0 right-3 flex items-center text-gray-400 hover:text-gray-600"
              >
                {showCurrentPassword ? <EyeOff size={18} /> : <Eye size={18} />}
              </button>
            </div>
          </div>

          <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1">
                New Password
              </label>
              <div className="relative">
                <Lock className="absolute left-3 top-1/2 -translate-y-1/2 text-gray-400" size={18} />
                <input
                  type={showNewPassword ? 'text' : 'password'}
                  value={passwords.new_password}
                  onChange={(e) => setPasswords({ ...passwords, new_password: e.target.value })}
                  className="w-full pl-10 pr-12 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-purple-500 focus:border-transparent text-gray-900"
                  placeholder="Enter new password"
                />
                <button
                  type="button"
                  onClick={() => setShowNewPassword(!showNewPassword)}
                  className="absolute inset-y-0 right-3 flex items-center text-gray-400 hover:text-gray-600"
                >
                  {showNewPassword ? <EyeOff size={18} /> : <Eye size={18} />}
                </button>
              </div>
            </div>

            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1">
                Confirm New Password
              </label>
              <div className="relative">
                <Lock className="absolute left-3 top-1/2 -translate-y-1/2 text-gray-400" size={18} />
                <input
                  type="password"
                  value={passwords.confirm_password}
                  onChange={(e) => setPasswords({ ...passwords, confirm_password: e.target.value })}
                  className="w-full pl-10 pr-4 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-purple-500 focus:border-transparent text-gray-900"
                  placeholder="Confirm new password"
                />
              </div>
            </div>
          </div>

          <div className="flex justify-end pt-4">
            <button
              type="submit"
              disabled={savingPassword || !passwords.current_password || !passwords.new_password}
              className="flex items-center gap-2 px-6 py-2 bg-orange-600 text-white rounded-lg hover:bg-orange-700 transition-colors disabled:opacity-50"
            >
              {savingPassword ? <Loader2 className="animate-spin" size={18} /> : <Shield size={18} />}
              Change Password
            </button>
          </div>
        </form>
      </div>

      {/* ──────────────── 2FA Section ──────────────── */}
      <div className="bg-white rounded-xl shadow-md p-6">
        <div className="flex items-center gap-3 mb-6">
          <div className={`p-3 rounded-lg ${twoFAEnabled ? 'bg-green-100' : 'bg-gray-100'}`}>
            <Smartphone className={twoFAEnabled ? 'text-green-600' : 'text-gray-400'} size={24} />
          </div>
          <div className="flex-1">
            <h2 className="text-xl font-bold text-gray-900">Two-Factor Authentication (2FA)</h2>
            <p className="text-gray-500 text-sm">Protect your account with Google Authenticator</p>
          </div>
          <span className={`px-3 py-1 rounded-full text-sm font-semibold ${twoFAEnabled
            ? 'bg-green-100 text-green-700'
            : 'bg-gray-100 text-gray-500'
            }`}>
            {twoFAEnabled ? '✅ Enabled' : 'Disabled'}
          </span>
        </div>

        {/* 2FA Messages */}
        {twoFAMessage && (
          <div className={`mb-4 p-4 rounded-lg flex items-center gap-2 ${twoFAMessage.type === 'success'
            ? 'bg-green-50 text-green-800 border border-green-200'
            : 'bg-red-50 text-red-800 border border-red-200'
            }`}>
            {twoFAMessage.type === 'success' ? <Check size={18} /> : <AlertTriangle size={18} />}
            {twoFAMessage.text}
          </div>
        )}

        {/* IDLE — not enabled */}
        {twoFAStep === 'idle' && !twoFAEnabled && (
          <div className="space-y-4">
            <div className="bg-blue-50 border border-blue-200 rounded-lg p-4">
              <p className="text-blue-800 text-sm">
                <strong>How it works:</strong> After enabling 2FA, you&apos;ll need your Google Authenticator app to generate a 6-digit code every time you log in.
              </p>
              <ol className="mt-2 text-blue-700 text-sm list-decimal list-inside space-y-1">
                <li>Install Google Authenticator on your phone</li>
                <li>Click &quot;Set up 2FA&quot; below to get a QR code</li>
                <li>Scan the QR code with the app</li>
                <li>Enter the 6-digit code to confirm</li>
              </ol>
            </div>
            <button
              id="btn-setup-2fa"
              onClick={handleSetup2FA}
              disabled={twoFALoading}
              className="flex items-center gap-2 px-6 py-2 bg-indigo-600 text-white rounded-lg hover:bg-indigo-700 transition-colors disabled:opacity-50"
            >
              {twoFALoading ? <Loader2 className="animate-spin" size={18} /> : <ShieldCheck size={18} />}
              Set up 2FA
            </button>
          </div>
        )}

        {/* SETUP — show QR code */}
        {twoFAStep === 'setup' && (
          <div className="space-y-4">
            <p className="text-gray-700 font-medium">Step 1: Scan this QR code with Google Authenticator</p>
            <div className="flex flex-col sm:flex-row gap-6 items-start">
              {qrCode && (
                <div className="border-2 border-gray-200 rounded-xl p-3 bg-white shadow-sm">
                  {/* eslint-disable-next-line @next/next/no-img-element */}
                  <img src={qrCode} alt="2FA QR Code" className="w-48 h-48" />
                </div>
              )}
              <div className="flex-1 space-y-3">
                <div>
                  <p className="text-sm text-gray-500 mb-1">Or enter this key manually:</p>
                  <div className="flex items-center gap-2 bg-gray-100 rounded-lg px-3 py-2">
                    <code className="text-sm font-mono text-gray-800 break-all">{totpSecret}</code>
                  </div>
                </div>
                <div className="bg-yellow-50 border border-yellow-200 rounded-lg p-3">
                  <p className="text-yellow-800 text-sm flex items-center gap-1">
                    <AlertTriangle size={14} /> After scanning, click &quot;Next&quot; to enter your first code.
                  </p>
                </div>
                <button
                  id="btn-next-2fa"
                  onClick={() => setTwoFAStep('confirm')}
                  className="flex items-center gap-2 px-6 py-2 bg-indigo-600 text-white rounded-lg hover:bg-indigo-700 transition-colors"
                >
                  <Check size={18} /> I&apos;ve scanned it → Next
                </button>
              </div>
            </div>
          </div>
        )}

        {/* CONFIRM — enter first code */}
        {twoFAStep === 'confirm' && (
          <div className="space-y-4">
            <p className="text-gray-700 font-medium">Step 2: Enter the 6-digit code from Google Authenticator</p>
            <div className="flex gap-3 items-center">
              <input
                id="input-totp-code"
                type="text"
                inputMode="numeric"
                maxLength={6}
                value={totpCode}
                onChange={(e) => setTotpCode(e.target.value.replace(/\D/g, ''))}
                className="w-40 text-center text-2xl font-mono tracking-[0.5em] px-4 py-3 border-2 border-indigo-300 rounded-xl focus:ring-2 focus:ring-indigo-500 focus:border-transparent text-gray-900"
                placeholder="000000"
                autoFocus
              />
              <button
                id="btn-confirm-2fa"
                onClick={handleConfirm2FA}
                disabled={twoFALoading || totpCode.length !== 6}
                className="flex items-center gap-2 px-6 py-3 bg-green-600 text-white rounded-xl hover:bg-green-700 transition-colors disabled:opacity-50 font-semibold"
              >
                {twoFALoading ? <Loader2 className="animate-spin" size={18} /> : <ShieldCheck size={18} />}
                Confirm & Enable
              </button>
            </div>
            {twoFAMessage?.type === 'error' && (
              <p className="text-red-600 text-sm flex items-center gap-1">
                <AlertTriangle size={14} /> {twoFAMessage.text}
              </p>
            )}
            <button onClick={() => setTwoFAStep('setup')} className="text-sm text-gray-400 hover:text-gray-600">
              ← Back to QR code
            </button>
          </div>
        )}

        {/* BACKUP — show backup codes */}
        {twoFAStep === 'backup' && (
          <div className="space-y-4">
            <div className="bg-green-50 border border-green-300 rounded-lg p-4">
              <p className="text-green-800 font-semibold flex items-center gap-2">
                <ShieldCheck size={18} /> 2FA successfully enabled! 🎉
              </p>
            </div>
            <div>
              <div className="flex items-center justify-between mb-2">
                <p className="text-gray-700 font-medium flex items-center gap-2">
                  <AlertTriangle size={16} className="text-orange-500" />
                  Save your backup codes — they can&apos;t be shown again!
                </p>
                <button
                  id="btn-copy-backup"
                  onClick={copyBackupCodes}
                  className="flex items-center gap-1 text-sm px-3 py-1 bg-gray-100 hover:bg-gray-200 rounded-lg transition-colors text-gray-700"
                >
                  {copiedBackup ? <><Check size={14} /> Copied!</> : <><Copy size={14} /> Copy all</>}
                </button>
              </div>
              <div className="grid grid-cols-2 sm:grid-cols-4 gap-2">
                {backupCodes.map((code, i) => (
                  <div key={i} className="bg-gray-900 text-green-400 font-mono text-sm text-center py-2 px-3 rounded-lg tracking-wider">
                    {code}
                  </div>
                ))}
              </div>
              <p className="text-gray-400 text-xs mt-2">Each code can only be used once. Store them somewhere safe (password manager, printed paper).</p>
            </div>
            <button
              onClick={() => setTwoFAStep('idle')}
              className="px-6 py-2 bg-indigo-600 text-white rounded-lg hover:bg-indigo-700 transition-colors"
            >
              Done
            </button>
          </div>
        )}

        {/* ENABLED — show status + disable option */}
        {twoFAEnabled && twoFAStep === 'idle' && (
          <div className="space-y-4">
            <div className="bg-green-50 border border-green-200 rounded-lg p-4 flex items-center gap-3">
              <ShieldCheck className="text-green-600 shrink-0" size={24} />
              <div>
                <p className="text-green-800 font-semibold">Your account is protected with 2FA</p>
                <p className="text-green-700 text-sm">Every login requires a code from Google Authenticator</p>
              </div>
            </div>
            {twoFAStep === 'idle' && (
              <details className="group">
                <summary className="cursor-pointer text-sm text-red-500 hover:text-red-700 flex items-center gap-1">
                  <ShieldX size={14} /> Disable 2FA (not recommended)
                </summary>
                <div className="mt-3 flex gap-3 items-center">
                  <input
                    id="input-disable-code"
                    type="text"
                    inputMode="numeric"
                    maxLength={6}
                    value={disableCode}
                    onChange={(e) => setDisableCode(e.target.value.replace(/\D/g, ''))}
                    className="w-36 text-center text-xl font-mono tracking-[0.4em] px-3 py-2 border-2 border-red-300 rounded-lg focus:ring-2 focus:ring-red-400 text-gray-900"
                    placeholder="000000"
                  />
                  <button
                    id="btn-disable-2fa"
                    onClick={handleDisable2FA}
                    disabled={twoFALoading || disableCode.length !== 6}
                    className="flex items-center gap-2 px-4 py-2 bg-red-600 text-white rounded-lg hover:bg-red-700 transition-colors disabled:opacity-50 text-sm"
                  >
                    {twoFALoading ? <Loader2 className="animate-spin" size={16} /> : <ShieldX size={16} />}
                    Disable 2FA
                  </button>
                </div>
              </details>
            )}
          </div>
        )}
      </div>
      {/* ──────────────── Passkeys (Passwordless) ──────────────── */}
      <div className="bg-white rounded-xl shadow-md p-6">
        <div className="flex items-center gap-3 mb-6">
          <div className="bg-indigo-100 p-3 rounded-lg">
            <span className="text-2xl">🔑</span>
          </div>
          <div>
            <h2 className="text-xl font-bold text-gray-900">Passkeys</h2>
            <p className="text-gray-500 text-sm">Login with fingerprint or Face ID — no password needed</p>
          </div>
        </div>
        <PasskeyManager />
      </div>

    </div>
  );
}
