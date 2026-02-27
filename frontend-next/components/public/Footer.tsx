'use client';

import Link from 'next/link';
import { Facebook, Instagram, Youtube, Linkedin, Mail } from 'lucide-react';
import { useEffect, useState } from 'react';
import { getApiUrl } from '@/lib/config';

// Custom SVG Icons
const XIcon = ({ size = 24 }: { size?: number }) => (
  <svg width={size} height={size} viewBox="0 0 24 24" fill="currentColor">
    <path d="M18.244 2.25h3.308l-7.227 8.26 8.502 11.24H16.17l-5.214-6.817L4.99 21.75H1.68l7.73-8.835L1.254 2.25H8.08l4.713 6.231zm-1.161 17.52h1.833L7.084 4.126H5.117z" />
  </svg>
);

const TikTokIcon = ({ size = 24 }: { size?: number }) => (
  <svg width={size} height={size} viewBox="0 0 24 24" fill="currentColor">
    <path d="M19.59 6.69a4.83 4.83 0 0 1-3.77-4.25V2h-3.45v13.67a2.89 2.89 0 0 1-5.2 1.74 2.89 2.89 0 0 1 2.31-4.64 2.93 2.93 0 0 1 .88.13V9.4a6.84 6.84 0 0 0-1-.05A6.33 6.33 0 0 0 5 20.1a6.34 6.34 0 0 0 10.86-4.43v-7a8.16 8.16 0 0 0 4.77 1.52v-3.4a4.85 4.85 0 0 1-1-.1z" />
  </svg>
);

const TelegramIcon = ({ size = 24 }: { size?: number }) => (
  <svg width={size} height={size} viewBox="0 0 24 24" fill="currentColor">
    <path d="M12 2C6.48 2 2 6.48 2 12s4.48 10 10 10 10-4.48 10-10S17.52 2 12 2zm4.64 6.8c-.15 1.58-.8 5.42-1.13 7.19-.14.75-.42 1-.68 1.03-.58.05-1.02-.38-1.58-.75-.88-.58-1.38-.94-2.23-1.5-.99-.65-.35-1.01.22-1.59.15-.15 2.71-2.48 2.76-2.69a.2.2 0 0 0-.05-.18c-.06-.05-.14-.03-.21-.02-.09.02-1.49.95-4.22 2.79-.4.27-.76.41-1.08.4-.36-.01-1.04-.2-1.55-.37-.63-.2-1.12-.31-1.08-.66.02-.18.27-.36.74-.55 2.92-1.27 4.86-2.11 5.83-2.51 2.78-1.16 3.35-1.36 3.73-1.36.08 0 .27.02.39.12.1.08.13.19.14.27-.01.06.01.24 0 .38z" />
  </svg>
);

interface SiteSettings {
  footer_text: string;
  facebook_url: string;
  facebook_enabled: boolean;
  twitter_url: string;
  twitter_enabled: boolean;
  instagram_url: string;
  instagram_enabled: boolean;
  youtube_url: string;
  youtube_enabled: boolean;
  linkedin_url: string;
  linkedin_enabled: boolean;
  tiktok_url: string;
  tiktok_enabled: boolean;
  telegram_url: string;
  telegram_enabled: boolean;
  // Page settings
  about_page_enabled: boolean;
  privacy_page_enabled: boolean;
  terms_page_enabled: boolean;
  contact_page_enabled: boolean;
}

interface Category {
  id: number;
  name: string;
  slug: string;
  article_count: number;
}

export default function Footer() {
  const [settings, setSettings] = useState<SiteSettings | null>(null);
  const [categories, setCategories] = useState<Category[]>([]);
  const [email, setEmail] = useState('');
  const [subscribeStatus, setSubscribeStatus] = useState<'idle' | 'loading' | 'success' | 'error'>('idle');

  useEffect(() => {    const apiUrl = getApiUrl();

    // Cache duration: 10 minutes
    const CACHE_DURATION = 10 * 60 * 1000;

    const loadData = async () => {
      try {
        // Try to load categories from cache
        const cachedCats = localStorage.getItem('freshmotors_categories');
        const cachedCatsTime = localStorage.getItem('freshmotors_categories_time');

        if (cachedCats && cachedCatsTime && (Date.now() - parseInt(cachedCatsTime) < CACHE_DURATION)) {
          setCategories(JSON.parse(cachedCats));
        } else {
          const res = await fetch(`${apiUrl}/categories/`);
          if (res.ok) {
            const data = await res.json();
            const cats = Array.isArray(data) ? data : data.results || [];
            const sortedCats = cats.sort((a: Category, b: Category) => a.name.localeCompare(b.name));
            setCategories(sortedCats);
            localStorage.setItem('freshmotors_categories', JSON.stringify(sortedCats));
            localStorage.setItem('freshmotors_categories_time', Date.now().toString());
          }
        }

        // Try to load settings from cache
        const cachedSettings = localStorage.getItem('freshmotors_settings');
        const cachedSettingsTime = localStorage.getItem('freshmotors_settings_time');

        if (cachedSettings && cachedSettingsTime && (Date.now() - parseInt(cachedSettingsTime) < CACHE_DURATION)) {
          setSettings(JSON.parse(cachedSettings));
        } else {
          const res = await fetch(`${apiUrl}/settings/`);
          if (res.ok) {
            const data = await res.json();
            setSettings(data);
            localStorage.setItem('freshmotors_settings', JSON.stringify(data));
            localStorage.setItem('freshmotors_settings_time', Date.now().toString());
          }
        }
      } catch (err) {
        console.error('Failed to load footer data:', err);
      }
    };

    loadData();
  }, []);

  const handleNewsletterSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!email.trim()) return;

    setSubscribeStatus('loading');

    try {
      const response = await fetch(`${getApiUrl()}/newsletter/subscribe/`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ email: email.trim() }),
      });

      if (response.ok) {
        setSubscribeStatus('success');
        setEmail('');

        // Track newsletter signup with GA4
        if (typeof window !== 'undefined' && (window as any).gtag) {
          (window as any).gtag('event', 'newsletter_signup', {
            method: 'footer_form',
          });
        }
      } else {
        const data = await response.json();
        if (data.message?.includes('subscribed')) {
          setSubscribeStatus('success'); // Already subscribed is still success
          setEmail('');
        } else {
          setSubscribeStatus('error');
        }
      }
    } catch (error) {
      console.error('Subscribe error:', error);
      setSubscribeStatus('error');
    }

    setTimeout(() => setSubscribeStatus('idle'), 3000);
  };

  const socialLinks = [
    { name: 'Facebook', icon: Facebook, url: settings?.facebook_url, enabled: settings?.facebook_enabled },
    { name: 'X', icon: XIcon, url: settings?.twitter_url, enabled: settings?.twitter_enabled },
    { name: 'Instagram', icon: Instagram, url: settings?.instagram_url, enabled: settings?.instagram_enabled },
    { name: 'YouTube', icon: Youtube, url: settings?.youtube_url, enabled: settings?.youtube_enabled },
    { name: 'LinkedIn', icon: Linkedin, url: settings?.linkedin_url, enabled: settings?.linkedin_enabled },
    { name: 'TikTok', icon: TikTokIcon, url: settings?.tiktok_url, enabled: settings?.tiktok_enabled },
    { name: 'Telegram', icon: TelegramIcon, url: settings?.telegram_url, enabled: settings?.telegram_enabled },
  ];

  const activeSocials = socialLinks.filter(s => s.enabled && s.url);

  return (
    <footer className="bg-gradient-to-r from-gray-800 to-gray-900 text-white mt-auto">
      <div className="container mx-auto px-4 py-12">
        {/* Newsletter Section */}
        <div className="bg-gradient-to-r from-purple-900/30 to-indigo-900/30 rounded-2xl p-8 mb-12 border border-purple-500/20">
          <div className="max-w-2xl mx-auto text-center">
            <Mail className="mx-auto mb-4 text-purple-400" size={40} />
            <h3 className="text-2xl font-bold mb-2 text-white">Subscribe to Our Newsletter</h3>
            <p className="text-gray-300 mb-6">
              Get the latest automotive news, reviews, and exclusive content delivered straight to your inbox.
            </p>
            <form onSubmit={handleNewsletterSubmit} className="flex flex-col sm:flex-row gap-3 max-w-md mx-auto">
              <input
                type="email"
                value={email}
                onChange={(e) => setEmail(e.target.value)}
                placeholder="Enter your email"
                required
                className="flex-1 px-4 py-3 rounded-lg bg-white/10 border border-white/20 text-white placeholder-gray-400 focus:outline-none focus:ring-2 focus:ring-purple-500 focus:border-transparent"
              />
              <button
                type="submit"
                disabled={subscribeStatus === 'loading'}
                className="px-6 py-3 bg-purple-600 hover:bg-purple-700 rounded-lg font-medium transition-colors disabled:opacity-50 disabled:cursor-not-allowed whitespace-nowrap"
              >
                {subscribeStatus === 'loading' ? 'Subscribing...' : 'Subscribe'}
              </button>
            </form>
            {subscribeStatus === 'success' && (
              <p className="mt-3 text-green-400 text-sm">✓ Successfully subscribed!</p>
            )}
          </div>
        </div>

        {/* Main Footer Content */}
        <div className="grid grid-cols-1 md:grid-cols-4 gap-8 mb-8">
          <div>
            <h3 className="text-xl font-bold mb-4 text-purple-400">Fresh Motors</h3>
            <p className="text-gray-300 text-sm mb-4">
              Your source for the latest automotive news, reviews, and insights.
            </p>
            <a
              href="mailto:info@freshmotors.net"
              className="text-gray-300 hover:text-purple-400 transition-colors text-sm flex items-center gap-2 mb-4"
            >
              <Mail size={16} />
              info@freshmotors.net
            </a>
            {activeSocials.length > 0 && (
              <div className="flex flex-wrap gap-2">
                {activeSocials.map((social) => {
                  const Icon = social.icon;
                  return (
                    <a
                      key={social.name}
                      href={social.url}
                      target="_blank"
                      rel="noopener noreferrer"
                      className="bg-white/10 hover:bg-purple-600 p-2 rounded-lg transition-all hover:scale-110"
                      title={social.name}
                    >
                      <Icon size={18} />
                    </a>
                  );
                })}
              </div>
            )}
          </div>

          <div>
            <h4 className="font-bold mb-4 text-purple-400">Quick Links</h4>
            <ul className="space-y-2 text-sm">
              <li><Link href="/" className="text-gray-300 hover:text-purple-400 transition-colors">Home</Link></li>
              <li><Link href="/articles" className="text-gray-300 hover:text-purple-400 transition-colors">All Articles</Link></li>
              <li><Link href="/categories/news" className="text-gray-300 hover:text-purple-400 transition-colors">News</Link></li>
              <li><Link href="/categories/reviews" className="text-gray-300 hover:text-purple-400 transition-colors">Reviews</Link></li>
            </ul>
          </div>

          <div>
            <h4 className="font-bold mb-4 text-purple-400">Categories</h4>
            <ul className="space-y-2 text-sm">
              {categories.length > 0 ? (
                categories.map((cat) => (
                  <li key={cat.id}>
                    <Link
                      href={`/categories/${cat.slug}`}
                      className="text-gray-300 hover:text-purple-400 transition-colors"
                    >
                      {cat.name}
                    </Link>
                  </li>
                ))
              ) : (
                <>
                  <li><Link href="/categories/news" className="text-gray-300 hover:text-purple-400 transition-colors">News</Link></li>
                  <li><Link href="/categories/reviews" className="text-gray-300 hover:text-purple-400 transition-colors">Reviews</Link></li>
                  <li><Link href="/articles" className="text-gray-300 hover:text-purple-400 transition-colors">All Articles</Link></li>
                </>
              )}
            </ul>
          </div>

          <div>
            <h4 className="font-bold mb-4 text-purple-400">Company</h4>
            <ul className="space-y-2 text-sm">
              {(settings?.about_page_enabled !== false) && (
                <li><Link href="/about" className="text-gray-300 hover:text-purple-400 transition-colors">About Us</Link></li>
              )}
              <li><Link href="/for-authors" className="text-gray-300 hover:text-purple-400 transition-colors font-bold text-indigo-400">For Authors</Link></li>
              {(settings?.contact_page_enabled !== false) && (
                <li><Link href="/contact" className="text-gray-300 hover:text-purple-400 transition-colors">Contact Us</Link></li>
              )}
              {(settings?.privacy_page_enabled !== false) && (
                <li><Link href="/privacy-policy" className="text-gray-300 hover:text-purple-400 transition-colors">Privacy Policy</Link></li>
              )}
              {(settings?.terms_page_enabled !== false) && (
                <li><Link href="/terms" className="text-gray-300 hover:text-purple-400 transition-colors">Terms of Service</Link></li>
              )}
              <li><a href="/feed.xml" target="_blank" rel="noopener noreferrer" className="text-gray-300 hover:text-purple-400 transition-colors">RSS Feed</a></li>
            </ul>
          </div>
        </div>

        <div className="border-t border-gray-700 pt-8 text-center text-gray-400 text-sm">
          <p>{settings?.footer_text || `© ${new Date().getFullYear()} Fresh Motors. All rights reserved.`}</p>
        </div>
      </div>
    </footer>
  );
}
