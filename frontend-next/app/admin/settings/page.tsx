'use client';

import { useState, useEffect } from 'react';
import { Save, Facebook, Instagram, Youtube, Linkedin, Wrench, AlertTriangle } from 'lucide-react';
import api from '@/lib/api';

// Custom SVG Icons
const XIcon = ({ size = 24 }: { size?: number }) => (
  <svg width={size} height={size} viewBox="0 0 24 24" fill="currentColor">
    <path d="M18.244 2.25h3.308l-7.227 8.26 8.502 11.24H16.17l-5.214-6.817L4.99 21.75H1.68l7.73-8.835L1.254 2.25H8.08l4.713 6.231zm-1.161 17.52h1.833L7.084 4.126H5.117z"/>
  </svg>
);

const TikTokIcon = ({ size = 24 }: { size?: number }) => (
  <svg width={size} height={size} viewBox="0 0 24 24" fill="currentColor">
    <path d="M19.59 6.69a4.83 4.83 0 0 1-3.77-4.25V2h-3.45v13.67a2.89 2.89 0 0 1-5.2 1.74 2.89 2.89 0 0 1 2.31-4.64 2.93 2.93 0 0 1 .88.13V9.4a6.84 6.84 0 0 0-1-.05A6.33 6.33 0 0 0 5 20.1a6.34 6.34 0 0 0 10.86-4.43v-7a8.16 8.16 0 0 0 4.77 1.52v-3.4a4.85 4.85 0 0 1-1-.1z"/>
  </svg>
);

const TelegramIcon = ({ size = 24 }: { size?: number }) => (
  <svg width={size} height={size} viewBox="0 0 24 24" fill="currentColor">
    <path d="M12 2C6.48 2 2 6.48 2 12s4.48 10 10 10 10-4.48 10-10S17.52 2 12 2zm4.64 6.8c-.15 1.58-.8 5.42-1.13 7.19-.14.75-.42 1-.68 1.03-.58.05-1.02-.38-1.58-.75-.88-.58-1.38-.94-2.23-1.5-.99-.65-.35-1.01.22-1.59.15-.15 2.71-2.48 2.76-2.69a.2.2 0 0 0-.05-.18c-.06-.05-.14-.03-.21-.02-.09.02-1.49.95-4.22 2.79-.4.27-.76.41-1.08.4-.36-.01-1.04-.2-1.55-.37-.63-.2-1.12-.31-1.08-.66.02-.18.27-.36.74-.55 2.92-1.27 4.86-2.11 5.83-2.51 2.78-1.16 3.35-1.36 3.73-1.36.08 0 .27.02.39.12.1.08.13.19.14.27-.01.06.01.24 0 .38z"/>
  </svg>
);

interface SocialNetwork {
  name: string;
  icon: any;
  urlField: string;
  enabledField: string;
  color: string;
}

const socialNetworks: SocialNetwork[] = [
  { name: 'Facebook', icon: Facebook, urlField: 'facebook_url', enabledField: 'facebook_enabled', color: 'bg-blue-600' },
  { name: 'X', icon: XIcon, urlField: 'twitter_url', enabledField: 'twitter_enabled', color: 'bg-black' },
  { name: 'Instagram', icon: Instagram, urlField: 'instagram_url', enabledField: 'instagram_enabled', color: 'bg-pink-600' },
  { name: 'YouTube', icon: Youtube, urlField: 'youtube_url', enabledField: 'youtube_enabled', color: 'bg-red-600' },
  { name: 'LinkedIn', icon: Linkedin, urlField: 'linkedin_url', enabledField: 'linkedin_enabled', color: 'bg-blue-700' },
  { name: 'TikTok', icon: TikTokIcon, urlField: 'tiktok_url', enabledField: 'tiktok_enabled', color: 'bg-black' },
  { name: 'Telegram', icon: TelegramIcon, urlField: 'telegram_url', enabledField: 'telegram_enabled', color: 'bg-blue-500' },
];

export default function SettingsPage() {
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);
  const [formData, setFormData] = useState<any>({
    site_name: '',
    site_description: '',
    contact_email: '',
    footer_text: '',
    maintenance_mode: false,
    maintenance_message: '',
    facebook_url: '',
    facebook_enabled: false,
    twitter_url: '',
    twitter_enabled: false,
    instagram_url: '',
    instagram_enabled: false,
    youtube_url: '',
    youtube_enabled: false,
    linkedin_url: '',
    linkedin_enabled: false,
    tiktok_url: '',
    tiktok_enabled: false,
    telegram_url: '',
    telegram_enabled: false,
  });

  useEffect(() => {
    fetchSettings();
  }, []);

  const fetchSettings = async () => {
    try {
      const response = await api.get('/settings/');
      setFormData(response.data);
    } catch (error) {
      console.error('Failed to fetch settings:', error);
    } finally {
      setLoading(false);
    }
  };

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setSaving(true);

    try {
      await api.put('/settings/1/', formData);
      alert('Settings saved successfully!');
    } catch (error: any) {
      console.error('Failed to save settings:', error);
      alert('Failed to save settings: ' + (error.response?.data?.detail || error.message));
    } finally {
      setSaving(false);
    }
  };

  if (loading) {
    return (
      <div className="flex items-center justify-center min-h-screen">
        <div className="text-center">
          <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-indigo-600 mx-auto"></div>
          <p className="text-gray-600 mt-4 font-medium">Loading settings...</p>
        </div>
      </div>
    );
  }

  return (
    <div>
      <div className="flex items-center justify-between mb-6">
        <h1 className="text-2xl sm:text-3xl font-black text-gray-950">Site Settings</h1>
      </div>

      <form onSubmit={handleSubmit} className="space-y-6">
        {/* Maintenance Mode - Top Priority */}
        <div className={`rounded-lg shadow-md p-6 border-2 ${formData.maintenance_mode ? 'bg-orange-50 border-orange-400' : 'bg-white border-transparent'}`}>
          <div className="flex items-center gap-3 mb-4">
            <div className={`p-3 rounded-lg ${formData.maintenance_mode ? 'bg-orange-500' : 'bg-gray-400'} text-white`}>
              <Wrench size={24} />
            </div>
            <div>
              <h2 className="text-xl font-bold text-gray-900">Maintenance Mode</h2>
              <p className="text-sm text-gray-500">Закрыть сайт на время обновления</p>
            </div>
          </div>

          <div className="space-y-4">
            {/* Toggle Switch */}
            <div className="flex items-center justify-between p-4 bg-white rounded-lg border border-gray-200">
              <div className="flex items-center gap-3">
                {formData.maintenance_mode && <AlertTriangle className="text-orange-500" size={20} />}
                <div>
                  <p className="font-bold text-gray-900">
                    {formData.maintenance_mode ? '🚧 Режим обслуживания ВКЛЮЧЕН' : 'Режим обслуживания выключен'}
                  </p>
                  <p className="text-sm text-gray-500">
                    {formData.maintenance_mode 
                      ? 'Посетители видят страницу "На ремонте". Вы как админ - видите сайт.' 
                      : 'Сайт доступен всем посетителям'}
                  </p>
                </div>
              </div>
              <label className="relative inline-flex items-center cursor-pointer">
                <input
                  type="checkbox"
                  checked={formData.maintenance_mode}
                  onChange={(e) => setFormData({ ...formData, maintenance_mode: e.target.checked })}
                  className="sr-only peer"
                />
                <div className="w-14 h-7 bg-gray-200 peer-focus:outline-none peer-focus:ring-4 peer-focus:ring-orange-300 rounded-full peer peer-checked:after:translate-x-full rtl:peer-checked:after:-translate-x-full peer-checked:after:border-white after:content-[''] after:absolute after:top-[2px] after:start-[2px] after:bg-white after:border-gray-300 after:border after:rounded-full after:h-6 after:w-6 after:transition-all peer-checked:bg-orange-500"></div>
              </label>
            </div>

            {/* Message */}
            {formData.maintenance_mode && (
              <div>
                <label className="block text-sm font-bold text-gray-900 mb-2">
                  Сообщение для посетителей
                </label>
                <textarea
                  value={formData.maintenance_message}
                  onChange={(e) => setFormData({ ...formData, maintenance_message: e.target.value })}
                  rows={3}
                  placeholder="Мы работаем над улучшением сайта. Пожалуйста, загляните позже!"
                  className="w-full px-4 py-3 border border-gray-300 rounded-lg focus:ring-2 focus:ring-orange-500 outline-none text-gray-900"
                />
              </div>
            )}
          </div>
        </div>

        {/* General Settings */}
        <div className="bg-white rounded-lg shadow-md p-6">
          <h2 className="text-xl font-bold text-gray-900 mb-6">General Settings</h2>
          
          <div className="space-y-4">
            <div>
              <label className="block text-sm font-bold text-gray-900 mb-2">Site Name</label>
              <input
                type="text"
                value={formData.site_name}
                onChange={(e) => setFormData({ ...formData, site_name: e.target.value })}
                className="w-full px-4 py-3 border border-gray-300 rounded-lg focus:ring-2 focus:ring-indigo-500 outline-none text-gray-900"
              />
            </div>

            <div>
              <label className="block text-sm font-bold text-gray-900 mb-2">Site Description</label>
              <textarea
                value={formData.site_description}
                onChange={(e) => setFormData({ ...formData, site_description: e.target.value })}
                rows={3}
                className="w-full px-4 py-3 border border-gray-300 rounded-lg focus:ring-2 focus:ring-indigo-500 outline-none text-gray-900"
              />
            </div>

            <div>
              <label className="block text-sm font-bold text-gray-900 mb-2">Contact Email</label>
              <input
                type="email"
                value={formData.contact_email}
                onChange={(e) => setFormData({ ...formData, contact_email: e.target.value })}
                className="w-full px-4 py-3 border border-gray-300 rounded-lg focus:ring-2 focus:ring-indigo-500 outline-none text-gray-900"
              />
            </div>

            <div>
              <label className="block text-sm font-bold text-gray-900 mb-2">Footer Text</label>
              <input
                type="text"
                value={formData.footer_text}
                onChange={(e) => setFormData({ ...formData, footer_text: e.target.value })}
                className="w-full px-4 py-3 border border-gray-300 rounded-lg focus:ring-2 focus:ring-indigo-500 outline-none text-gray-900"
              />
            </div>
          </div>
        </div>

        {/* Social Networks */}
        <div className="bg-white rounded-lg shadow-md p-6">
          <h2 className="text-xl font-bold text-gray-900 mb-6">Social Networks</h2>
          
          <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
            {socialNetworks.map((social) => {
              const Icon = social.icon;
              return (
                <div key={social.name} className="border-2 border-gray-200 rounded-lg p-4 hover:border-indigo-300 transition-colors">
                  <div className="flex items-center gap-3 mb-4">
                    <div className={`${social.color} p-2 rounded-lg text-white`}>
                      <Icon size={24} />
                    </div>
                    <h3 className="text-lg font-bold text-gray-900">{social.name}</h3>
                  </div>

                  <div className="space-y-3">
                    <div className="flex items-center gap-3">
                      <input
                        type="checkbox"
                        checked={formData[social.enabledField]}
                        onChange={(e) => setFormData({ ...formData, [social.enabledField]: e.target.checked })}
                        className="w-5 h-5 text-indigo-600 rounded focus:ring-2 focus:ring-indigo-500"
                      />
                      <label className="text-sm font-medium text-gray-700">
                        Show in footer
                      </label>
                    </div>

                    <input
                      type="url"
                      placeholder={`https://${social.name.toLowerCase()}.com/yourpage`}
                      value={formData[social.urlField]}
                      onChange={(e) => setFormData({ ...formData, [social.urlField]: e.target.value })}
                      className="w-full px-4 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-indigo-500 outline-none text-gray-900 text-sm"
                      disabled={!formData[social.enabledField]}
                    />
                  </div>
                </div>
              );
            })}
          </div>
        </div>

        {/* Save Button */}
        <div className="flex justify-end">
          <button
            type="submit"
            disabled={saving}
            className="bg-gradient-to-r from-indigo-600 to-purple-600 text-white px-8 py-3 rounded-lg font-bold hover:from-indigo-700 hover:to-purple-700 transition-all disabled:opacity-50 disabled:cursor-not-allowed shadow-md flex items-center gap-2"
          >
            {saving ? (
              <>
                <div className="animate-spin rounded-full h-5 w-5 border-b-2 border-white"></div>
                Saving...
              </>
            ) : (
              <>
                <Save size={20} />
                Save Settings
              </>
            )}
          </button>
        </div>
      </form>
    </div>
  );
}
