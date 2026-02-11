'use client';

import { GoogleLogin, CredentialResponse } from '@react-oauth/google';
import { useRouter } from 'next/navigation';
import { useState } from 'react';

interface GoogleLoginButtonProps {
    onSuccess?: () => void;
    onError?: (error: string) => void;
}

export default function GoogleLoginButton({ onSuccess, onError }: GoogleLoginButtonProps) {
    const router = useRouter();
    const [isLoading, setIsLoading] = useState(false);
    const clientId = process.env.NEXT_PUBLIC_GOOGLE_CLIENT_ID;

    // Don't render Google button if client ID is not configured
    // This prevents crashes during SSG/prerendering in CI where the env var isn't set
    if (!clientId) {
        return null;
    }

    const handleSuccess = async (credentialResponse: CredentialResponse) => {
        if (!credentialResponse.credential) {
            onError?.('No credential received from Google');
            return;
        }

        setIsLoading(true);

        try {
            const response = await fetch(`${process.env.NEXT_PUBLIC_API_URL}/users/google_oauth/`, {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                },
                body: JSON.stringify({
                    credential: credentialResponse.credential,
                }),
            });

            if (!response.ok) {
                const errorData = await response.json();
                throw new Error(errorData.detail || 'Google authentication failed');
            }

            const data = await response.json();

            // Store tokens
            localStorage.setItem('access_token', data.access);
            localStorage.setItem('refresh_token', data.refresh);

            // Store user info
            localStorage.setItem('user', JSON.stringify(data.user));

            // Notify other components (e.g., Header) about auth state change
            window.dispatchEvent(new Event('authChange'));

            onSuccess?.();

            // Redirect to home page
            router.push('/');
            router.refresh();
        } catch (error) {
            console.error('Google OAuth error:', error);
            onError?.(error instanceof Error ? error.message : 'Authentication failed');
        } finally {
            setIsLoading(false);
        }
    };

    const handleError = () => {
        onError?.('Google login failed');
    };

    return (
        <div className="google-login-wrapper">
            {isLoading ? (
                <div className="flex items-center justify-center p-2">
                    <div className="animate-spin rounded-full h-5 w-5 border-b-2 border-blue-600"></div>
                </div>
            ) : (
                <GoogleLogin
                    onSuccess={handleSuccess}
                    onError={handleError}
                    theme="outline"
                    size="large"
                    text="continue_with"
                    shape="rectangular"
                />
            )}
        </div>
    );
}
