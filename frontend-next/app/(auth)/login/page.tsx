'use client';

import { useState, useEffect, useRef } from 'react';
import Image from 'next/image';
import { Eye, EyeOff, Smartphone, ShieldCheck, Fingerprint } from 'lucide-react';
import '../register/register-password.css';
import { useRouter } from 'next/navigation';
import { login, login2FA, loginGoogle2FA, TwoFARequiredError, PasskeyRequiredError } from '@/lib/auth';
import { verifyPendingPasskey, browserSupportsWebAuthn } from '@/lib/passkey';
import Link from 'next/link';
import toast from 'react-hot-toast';
import GoogleLoginButton from '@/components/auth/GoogleLoginButton';

export default function LoginPage() {
  const router = useRouter();
  const [formData, setFormData] = useState({ username: '', password: '' });
  const [showPassword, setShowPassword] = useState(false);
  const [error, setError] = useState('');
  const [success, setSuccess] = useState('');
  const [isLoading, setIsLoading] = useState(false);
  const [isPasskeyLoading, setIsPasskeyLoading] = useState(false);
  const [passkeySupported, setPasskeySupported] = useState(false);

  // 2FA state — store credentials for step 2 (backend needs username+password+totp_code)
  const [requires2FA, setRequires2FA] = useState(false);
  const [requiresPasskey, setRequiresPasskey] = useState(false); // step between password and 2FA
  const [pending2FACredentials, setPending2FACredentials] = useState({ username: '', password: '' });
  const [googleUserId, setGoogleUserId] = useState(''); // set when 2FA triggered from Google OAuth
  const [totpCode, setTotpCode] = useState('');
  const totpInputRef = useRef<HTMLInputElement>(null);

  // Google OAuth 2FA — called when backend returns requires_2fa for staff user
  const handleGoogleRequires2FA = (userId: string) => {
    setGoogleUserId(userId);
    setRequires2FA(true);
  };

  // Redirect if already logged in
  useEffect(() => {
    const token = document.cookie.split(';').find(c => c.trim().startsWith('access_token='));
    if (token) router.replace('/');
    setPasskeySupported(browserSupportsWebAuthn());
  }, [router]);

  // Check for registration success message
  useEffect(() => {
    if (typeof window !== 'undefined') {
      const params = new URLSearchParams(window.location.search);
      if (params.get('registered') === 'true') {
        setSuccess('Account created successfully! Please login.');
      }
    }
  }, []);

  // Auto-focus TOTP input when 2FA step appears
  useEffect(() => {
    if (requires2FA) {
      setTimeout(() => totpInputRef.current?.focus(), 100);
    }
  }, [requires2FA]);

  const onLoginSuccess = () => {
    const userData = localStorage.getItem('user');
    if (userData) {
      const user = JSON.parse(userData);
      toast.success(`Welcome back, ${user.username}! 🎉`, {
        duration: 3000,
        position: 'top-center',
        style: {
          background: '#10B981', color: '#fff',
          fontWeight: 'bold', fontSize: '16px',
          padding: '16px 24px', borderRadius: '12px',
        },
        icon: '✨',
      });
    } else {
      toast.success('Login successful!');
    }
    setTimeout(() => { window.location.href = '/'; }, 500);
  };

  const handlePasskeyVerify = async () => {
    setIsPasskeyLoading(true);
    setError('');
    try {
      const { access } = await verifyPendingPasskey();
      const { getCurrentUser } = await import('@/lib/auth');
      const userData = await getCurrentUser(access);
      if (userData) localStorage.setItem('user', JSON.stringify(userData));
      toast.success('Welcome back! 🔑', {
        duration: 3000, position: 'top-center',
        style: { background: '#6366f1', color: '#fff', fontWeight: 'bold', fontSize: '16px', padding: '16px 24px', borderRadius: '12px' },
        icon: '👍',
      });
      setTimeout(() => { window.location.href = '/'; }, 500);
    } catch (err: unknown) {
      const msg = err instanceof Error ? err.message : 'Passkey verification failed';
      if (!msg.includes('AbortError') && !msg.includes('NotAllowedError')) {
        toast.error(msg); setError(msg);
      }
    } finally {
      setIsPasskeyLoading(false);
    }
  };

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setError('');
    setSuccess('');
    setIsLoading(true);

    try {
      await login(formData);
      onLoginSuccess();
    } catch (err: unknown) {
      // Passkey required — backend validated password, stored JWT, needs biometric
      if (err instanceof PasskeyRequiredError) {
        setRequiresPasskey(true);
        setIsLoading(false);
        return;
      }
      // 2FA required — save credentials so step 2 can re-authenticate
      if (err instanceof TwoFARequiredError) {
        setPending2FACredentials({ username: formData.username, password: formData.password });
        setRequires2FA(true);
        setIsLoading(false);
        return;
      }
      const e = err as { response?: { data?: { detail?: string } } };
      const errorMessage = e.response?.data?.detail || 'Invalid credentials';
      setError(errorMessage);
      toast.error(errorMessage, { duration: 4000, position: 'top-center' });
    } finally {
      setIsLoading(false);
    }
  };

  const handleTotpSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (totpCode.length !== 6) return;
    setError('');
    setIsLoading(true);

    try {
      // Google OAuth 2FA path uses googleUserId; regular login uses username+password
      if (googleUserId) {
        await loginGoogle2FA(googleUserId, totpCode);
      } else {
        await login2FA(pending2FACredentials.username, pending2FACredentials.password, totpCode);
      }
      onLoginSuccess();
    } catch {
      setError('Invalid code. Please check your Google Authenticator and try again.');
      setTotpCode('');
      totpInputRef.current?.focus();
    } finally {
      setIsLoading(false);
    }
  };

  return (
    <div className="min-h-screen bg-gradient-to-br from-slate-900 via-purple-900 to-slate-800 flex items-center justify-center px-4 py-8">
      <div className="max-w-md w-full">
        <div className="bg-white rounded-2xl shadow-2xl p-5 sm:p-8">

          {/* Logo */}
          <div className="text-center mb-6 pb-6 border-b border-gray-100">
            <Link href="/" className="inline-block hover:scale-105 transition-transform duration-300">
              <Image
                src="/logo.png"
                alt="Fresh Motors"
                width={400}
                height={100}
                className="h-[110px] sm:h-[160px] w-auto object-contain mx-auto scale-x-[1.5]"
                priority
              />
            </Link>
          </div>

          {/* ── STEP 2: 2FA TOTP input ── */}
          {requires2FA ? (
            <form onSubmit={handleTotpSubmit} className="space-y-6">
              <div className="text-center space-y-2">
                <div className="inline-flex items-center justify-center w-14 h-14 rounded-full bg-indigo-100 mb-2">
                  <Smartphone className="text-indigo-600" size={28} />
                </div>
                <h2 className="text-xl font-bold text-gray-900">Two-Factor Authentication</h2>
                <p className="text-gray-500 text-sm">
                  Open <strong>Google Authenticator</strong> and enter the 6-digit code for <strong>FreshMotors</strong>
                </p>
              </div>

              {error && (
                <div className="bg-red-50 border border-red-200 text-red-700 px-4 py-3 rounded text-sm">
                  {error}
                </div>
              )}

              <div className="flex justify-center">
                <input
                  ref={totpInputRef}
                  id="totp-code"
                  type="text"
                  inputMode="numeric"
                  maxLength={6}
                  value={totpCode}
                  onChange={(e) => setTotpCode(e.target.value.replace(/\D/g, ''))}
                  className="w-full text-center text-4xl font-mono tracking-[0.5em] px-6 py-5 border-2 border-indigo-300 rounded-xl focus:ring-2 focus:ring-indigo-500 focus:border-transparent outline-none text-gray-900 bg-gray-50"
                  placeholder="······"
                  autoComplete="one-time-code"
                />
              </div>

              <button
                type="submit"
                disabled={isLoading || totpCode.length !== 6}
                className="w-full flex items-center justify-center gap-2 bg-gradient-to-r from-indigo-600 to-indigo-700 text-white py-3 rounded-lg font-semibold hover:from-indigo-700 hover:to-indigo-800 transition-all disabled:opacity-50 disabled:cursor-not-allowed shadow-lg"
              >
                <ShieldCheck size={20} />
                {isLoading ? 'Verifying...' : 'Verify & Login'}
              </button>

              <button
                type="button"
                onClick={() => { setRequires2FA(false); setTotpCode(''); setError(''); setPending2FACredentials({ username: '', password: '' }); setGoogleUserId(''); }}
                className="w-full text-sm text-gray-400 hover:text-gray-600 transition-colors"
              >
                ← Back to login
              </button>
            </form>
          ) : requiresPasskey ? (
            /* ── STEP 1.5: Passkey verification (after password, before JWT) ── */
            <div className="space-y-6">
              <div className="text-center space-y-2">
                <div className="inline-flex items-center justify-center w-14 h-14 rounded-full bg-violet-100 mb-2">
                  <Fingerprint className="text-violet-600" size={28} />
                </div>
                <h2 className="text-xl font-bold text-gray-900">Verify with Passkey</h2>
                <p className="text-gray-500 text-sm">
                  Tap the button and confirm with your fingerprint or Face ID
                </p>
              </div>
              {error && (
                <div className="bg-red-50 border border-red-200 text-red-700 px-4 py-3 rounded text-sm">{error}</div>
              )}
              <button
                type="button"
                onClick={handlePasskeyVerify}
                disabled={isPasskeyLoading}
                className="w-full flex items-center justify-center gap-2.5 bg-gradient-to-r from-violet-600 to-indigo-600 text-white py-3.5 rounded-xl font-semibold hover:from-violet-700 hover:to-indigo-700 transition-all disabled:opacity-50 shadow-lg shadow-violet-500/30 text-base"
              >
                <Fingerprint size={22} className={isPasskeyLoading ? 'animate-pulse' : ''} />
                {isPasskeyLoading ? 'Waiting for biometric...' : 'Tap to confirm with fingerprint'}
              </button>
              <button
                type="button"
                onClick={() => { setRequiresPasskey(false); setError(''); }}
                className="w-full text-sm text-gray-400 hover:text-gray-600 transition-colors"
              >
                ← Back to login
              </button>
            </div>
          ) : (
            /* ── STEP 1: username + password ── */
            <form onSubmit={handleSubmit} className="space-y-6">
              {success && (
                <div className="bg-green-50 border border-green-200 text-green-700 px-4 py-3 rounded">
                  {success}
                </div>
              )}
              {error && (
                <div className="bg-red-50 border border-red-200 text-red-700 px-4 py-3 rounded">
                  {error}
                </div>
              )}


              <div>
                <label htmlFor="username" className="block text-sm font-medium text-gray-700 mb-2">
                  Username
                </label>
                <input
                  id="username"
                  type="text"
                  value={formData.username}
                  onChange={(e) => setFormData({ ...formData, username: e.target.value })}
                  className="w-full px-4 py-3 border border-gray-300 rounded-lg focus:ring-2 focus:ring-indigo-500 focus:border-transparent outline-none transition text-gray-900 bg-white"
                  required
                />
              </div>

              <div className="relative">
                <label htmlFor="password" className="block text-sm font-medium text-gray-700 mb-2">
                  Password
                </label>
                <input
                  id="password"
                  type={showPassword ? 'text' : 'password'}
                  value={formData.password}
                  onChange={(e) => setFormData({ ...formData, password: e.target.value })}
                  className="w-full px-4 py-3 border border-gray-300 rounded-lg focus:ring-2 focus:ring-indigo-500 focus:border-transparent outline-none transition text-gray-900 bg-white pr-12"
                  required
                  autoComplete="current-password"
                />
                <button
                  type="button"
                  tabIndex={-1}
                  aria-label={showPassword ? 'Hide password' : 'Show password'}
                  onClick={() => setShowPassword((v) => !v)}
                  className="absolute top-[2.75rem] right-3 flex items-center text-gray-400 hover:text-indigo-600 focus:outline-none"
                  style={{ background: 'none', border: 'none', padding: 0 }}
                >
                  {showPassword ? <EyeOff size={22} /> : <Eye size={22} />}
                </button>
              </div>

              <button
                type="submit"
                disabled={isLoading}
                className="w-full bg-gradient-to-r from-indigo-600 to-indigo-700 text-white py-3 rounded-lg font-semibold hover:from-indigo-700 hover:to-indigo-800 transition-all disabled:opacity-50 disabled:cursor-not-allowed shadow-lg"
              >
                {isLoading ? 'Logging in...' : 'Login'}
              </button>
            </form>
          )}

          {/* Google OAuth — step 1 only */}
          {!requires2FA && process.env.NEXT_PUBLIC_GOOGLE_CLIENT_ID && (
            <>
              <div className="relative my-6">
                <div className="absolute inset-0 flex items-center">
                  <div className="w-full border-t border-gray-300"></div>
                </div>
                <div className="relative flex justify-center text-sm">
                  <span className="px-2 bg-white text-gray-500">Or continue with</span>
                </div>
              </div>
              <div className="mb-6">
                <GoogleLoginButton
                  onSuccess={() => {
                    const userData = localStorage.getItem('user');
                    if (userData) {
                      const user = JSON.parse(userData);
                      toast.success(`Welcome back, ${user.username}! 🎉`, { duration: 3000, icon: '✨' });
                    }
                    setTimeout(() => { window.location.href = '/'; }, 500);
                  }}
                  onError={(err) => { toast.error(err); }}
                  onRequires2FA={handleGoogleRequires2FA}
                />
              </div>
            </>
          )}

          {!requires2FA && (
            <div className="mt-6 text-center space-y-2">
              <p className="text-gray-600 text-sm">
                Don&apos;t have an account?{' '}
                <Link href="/register" className="text-indigo-600 hover:underline font-medium">
                  Register here
                </Link>
              </p>
              <Link href="/" className="block text-indigo-600 hover:underline font-medium">
                ← Back to Home
              </Link>
            </div>
          )}

        </div>
      </div>
    </div>
  );
}
