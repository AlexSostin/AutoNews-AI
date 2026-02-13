'use client';

import { useState, useEffect } from 'react';
import { Shield, Lock, Eye, Database, Cookie, Mail, Loader2 } from 'lucide-react';
import { getApiUrl } from '@/lib/api';

interface SiteSettings {
  privacy_page_title: string;
  privacy_page_content: string;
  privacy_page_enabled: boolean;
}

export default function PrivacyPolicyPage() {
  const [settings, setSettings] = useState<SiteSettings | null>(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    fetchSettings();
  }, []);

  const fetchSettings = async () => {
    try {
      const apiUrl = getApiUrl();
      const response = await fetch(`${apiUrl}/settings/`);
      if (response.ok) {
        const data = await response.json();
        setSettings(data);
      }
    } catch (error) {
      console.error('Failed to fetch settings:', error);
    } finally {
      setLoading(false);
    }
  };

  const pageTitle = settings?.privacy_page_title || 'Privacy Policy';
  const pageContent = settings?.privacy_page_content || '';
  const hasCustomContent = pageContent.trim().length > 0;

  if (loading) {
    return (
      <main className="flex-1 bg-gray-50 flex items-center justify-center min-h-[60vh]">
        <Loader2 className="animate-spin text-purple-600" size={48} />
      </main>
    );
  }

  return (
    <>

      <main className="flex-1 bg-gray-50">
        {/* Hero Section */}
        <div className="bg-gradient-to-r from-slate-900 via-purple-900 to-gray-900 text-white py-16">
          <div className="container mx-auto px-4 text-center">
            <Shield className="mx-auto mb-4 text-purple-300" size={48} />
            <h1 className="text-4xl md:text-5xl font-black mb-4">{pageTitle}</h1>
            <p className="text-lg text-gray-300 max-w-2xl mx-auto">
              Last Updated: January 17, 2026
            </p>
          </div>
        </div>

        <div className="container mx-auto px-4 py-12 max-w-4xl">
          <div className="bg-white rounded-2xl shadow-lg p-8 md:p-12">
            {hasCustomContent ? (
              /* Custom Content from Admin */
              <div
                className="prose prose-lg max-w-none text-gray-700"
                dangerouslySetInnerHTML={{ __html: pageContent }}
              />
            ) : (
              /* Default Content */
              <>
                {/* Introduction */}
                <section className="mb-10">
                  <p className="text-gray-700 mb-4">
                    At Fresh Motors, we take your privacy seriously. This Privacy Policy explains how we collect,
                    use, disclose, and safeguard your information when you visit our website. Please read this
                    privacy policy carefully. If you do not agree with the terms of this privacy policy,
                    please do not access the site.
                  </p>
                  <p className="text-gray-700">
                    We reserve the right to make changes to this Privacy Policy at any time and for any reason.
                    We will alert you about any changes by updating the "Last Updated" date of this Privacy Policy.
                  </p>
                </section>

                {/* Collection of Information */}
                <section className="mb-10">
                  <div className="flex items-center gap-3 mb-4">
                    <div className="bg-purple-100 p-2 rounded-lg">
                      <Database className="text-purple-600" size={24} />
                    </div>
                    <h2 className="text-2xl font-black text-gray-900">Information We Collect</h2>
                  </div>

                  <h3 className="text-lg font-bold text-gray-900 mb-2">Personal Data</h3>
                  <p className="text-gray-700 mb-4">
                    We may collect personally identifiable information, such as your name and email address,
                    that you voluntarily give to us when you:
                  </p>
                  <ul className="list-disc list-inside text-gray-700 mb-4 space-y-1 ml-4">
                    <li>Subscribe to our newsletter</li>
                    <li>Submit comments or contact forms</li>
                    <li>Register for an account (if applicable)</li>
                    <li>Participate in surveys or contests</li>
                  </ul>

                  <h3 className="text-lg font-bold text-gray-900 mb-2">Derivative Data</h3>
                  <p className="text-gray-700 mb-4">
                    Our servers may automatically collect information when you access our website, such as:
                  </p>
                  <ul className="list-disc list-inside text-gray-700 mb-4 space-y-1 ml-4">
                    <li>IP address</li>
                    <li>Browser type and version</li>
                    <li>Operating system</li>
                    <li>Referral URLs</li>
                    <li>Pages viewed and time spent on pages</li>
                  </ul>
                </section>

                {/* Use of Information */}
                <section className="mb-10">
                  <div className="flex items-center gap-3 mb-4">
                    <div className="bg-indigo-100 p-2 rounded-lg">
                      <Eye className="text-indigo-600" size={24} />
                    </div>
                    <h2 className="text-2xl font-black text-gray-900">How We Use Your Information</h2>
                  </div>

                  <p className="text-gray-700 mb-4">
                    We may use the information we collect from you to:
                  </p>
                  <ul className="list-disc list-inside text-gray-700 space-y-2 ml-4">
                    <li>Send you our newsletter and promotional materials (with your consent)</li>
                    <li>Respond to your comments, questions, and requests</li>
                    <li>Improve our website and user experience</li>
                    <li>Analyze website usage and trends</li>
                    <li>Detect, prevent, and address technical issues</li>
                    <li>Send you administrative information, such as updates to our policies</li>
                  </ul>
                </section>

                {/* Cookies */}
                <section className="mb-10">
                  <div className="flex items-center gap-3 mb-4">
                    <div className="bg-blue-100 p-2 rounded-lg">
                      <Cookie className="text-blue-600" size={24} />
                    </div>
                    <h2 className="text-2xl font-black text-gray-900">Cookies and Tracking Technologies</h2>
                  </div>

                  <p className="text-gray-700 mb-4">
                    We may use cookies, web beacons, tracking pixels, and other tracking technologies to help
                    customize the website and improve your experience. Most web browsers are set to accept
                    cookies by default. You can choose to set your browser to remove or reject cookies, but
                    this may affect the availability and functionality of our website.
                  </p>
                  <p className="text-gray-700">
                    We may also use third-party analytics tools (such as Google Analytics) to help us understand
                    how users engage with our website.
                  </p>
                </section>

                {/* Google Advertising */}
                <section className="mb-10">
                  <div className="flex items-center gap-3 mb-4">
                    <div className="bg-yellow-100 p-2 rounded-lg">
                      <Eye className="text-yellow-600" size={24} />
                    </div>
                    <h2 className="text-2xl font-black text-gray-900">Google Advertising</h2>
                  </div>

                  <p className="text-gray-700 mb-4">
                    We use Google AdSense to display advertisements on our website. Google AdSense is an advertising
                    service provided by Google LLC. Third-party vendors, including Google, use cookies to serve ads
                    based on your prior visits to this website or other websites.
                  </p>
                  <p className="text-gray-700 mb-4">
                    Google&apos;s use of advertising cookies enables it and its partners to serve ads to you based on
                    your visit to our site and/or other sites on the Internet. You may opt out of personalised
                    advertising by visiting{' '}
                    <a href="https://www.google.com/settings/ads" className="text-purple-600 hover:text-purple-800 font-medium underline" target="_blank" rel="noopener noreferrer">
                      Google Ads Settings
                    </a>.
                  </p>
                  <p className="text-gray-700 mb-4">
                    For more information about how Google uses data when you use our website, please visit{' '}
                    <a href="https://policies.google.com/technologies/partner-sites" className="text-purple-600 hover:text-purple-800 font-medium underline" target="_blank" rel="noopener noreferrer">
                      How Google uses data when you use our partners&apos; sites or apps
                    </a>.
                  </p>
                  <p className="text-gray-700">
                    Third-party ad servers or ad networks may use technologies such as cookies, JavaScript,
                    or web beacons in their respective advertisements and links that appear on our website.
                    These technologies are used to measure the effectiveness of their advertising campaigns
                    and/or to personalise the advertising content that you see. Fresh Motors has no access to
                    or control over these cookies that are used by third-party advertisers.
                  </p>
                </section>

                {/* Disclosure of Information */}
                <section className="mb-10">
                  <div className="flex items-center gap-3 mb-4">
                    <div className="bg-green-100 p-2 rounded-lg">
                      <Lock className="text-green-600" size={24} />
                    </div>
                    <h2 className="text-2xl font-black text-gray-900">Disclosure of Your Information</h2>
                  </div>

                  <p className="text-gray-700 mb-4">
                    We may share information we have collected about you in certain situations:
                  </p>
                  <ul className="list-disc list-inside text-gray-700 space-y-2 ml-4">
                    <li><strong>By Law or to Protect Rights:</strong> If we believe disclosure is necessary to comply with applicable law or to protect our rights and safety.</li>
                    <li><strong>Third-Party Service Providers:</strong> We may share your information with third parties that perform services for us (e.g., email service providers, analytics providers).</li>
                    <li><strong>Business Transfers:</strong> In connection with any merger, sale of company assets, or acquisition.</li>
                  </ul>
                </section>

                {/* Third-Party Websites */}
                <section className="mb-10">
                  <h2 className="text-2xl font-black text-gray-900 mb-4">Third-Party Websites</h2>
                  <p className="text-gray-700">
                    Our website may contain links to third-party websites and applications. We are not responsible
                    for the privacy practices of these third parties. We encourage you to review their privacy
                    policies before providing any personal information.
                  </p>
                </section>

                {/* Security */}
                <section className="mb-10">
                  <h2 className="text-2xl font-black text-gray-900 mb-4">Security of Your Information</h2>
                  <p className="text-gray-700">
                    We use administrative, technical, and physical security measures to protect your personal
                    information. However, no security system is impenetrable, and we cannot guarantee the absolute
                    security of our systems or your information.
                  </p>
                </section>

                {/* Your Rights */}
                <section className="mb-10">
                  <h2 className="text-2xl font-black text-gray-900 mb-4">Your Rights</h2>
                  <p className="text-gray-700 mb-4">
                    Depending on your location, you may have the following rights regarding your personal information:
                  </p>
                  <ul className="list-disc list-inside text-gray-700 space-y-2 ml-4">
                    <li>Access, correct, or delete your personal information</li>
                    <li>Object to or restrict certain processing of your data</li>
                    <li>Withdraw consent for data processing</li>
                    <li>Data portability</li>
                  </ul>
                </section>

                {/* International Users & GDPR */}
                <section className="mb-10">
                  <h2 className="text-2xl font-black text-gray-900 mb-4">International Users & GDPR</h2>
                  <p className="text-gray-700 mb-4">
                    If you are located in the European Economic Area (EEA), United Kingdom, or other regions with
                    data protection laws, you have additional rights under the General Data Protection Regulation (GDPR)
                    and similar legislation:
                  </p>
                  <ul className="list-disc list-inside text-gray-700 space-y-2 ml-4">
                    <li><strong>Right to Access:</strong> Request a copy of your personal data</li>
                    <li><strong>Right to Rectification:</strong> Request correction of inaccurate data</li>
                    <li><strong>Right to Erasure:</strong> Request deletion of your data ("right to be forgotten")</li>
                    <li><strong>Right to Restrict Processing:</strong> Limit how we use your data</li>
                    <li><strong>Right to Data Portability:</strong> Receive your data in a portable format</li>
                    <li><strong>Right to Object:</strong> Object to processing based on legitimate interests</li>
                  </ul>
                  <p className="text-gray-700 mt-4">
                    For users in California (USA), you may have additional rights under the California Consumer
                    Privacy Act (CCPA) and California Privacy Rights Act (CPRA), including the right to know what
                    personal information is collected and the right to opt-out of the sale of personal information.
                    We do not sell personal information.
                  </p>
                  <p className="text-gray-700 mt-4">
                    For users in Canada, your privacy rights are protected under the Personal Information Protection
                    and Electronic Documents Act (PIPEDA) and provincial privacy laws.
                  </p>
                </section>

                {/* Children's Privacy */}
                <section className="mb-10">
                  <h2 className="text-2xl font-black text-gray-900 mb-4">Children's Privacy</h2>
                  <p className="text-gray-700">
                    Our website is not intended for children under the age of 16. We do not knowingly collect
                    personal information from children under 16. If you are a parent or guardian and believe your
                    child has provided us with personal information, please contact us immediately, and we will
                    take steps to delete such information from our systems.
                  </p>
                </section>

                {/* Newsletter */}
                <section className="mb-10">
                  <div className="flex items-center gap-3 mb-4">
                    <div className="bg-purple-100 p-2 rounded-lg">
                      <Mail className="text-purple-600" size={24} />
                    </div>
                    <h2 className="text-2xl font-black text-gray-900">Newsletter and Marketing</h2>
                  </div>
                  <p className="text-gray-700">
                    If you subscribe to our newsletter, we will send you periodic emails about automotive news,
                    articles, and updates. You can unsubscribe at any time by clicking the unsubscribe link at
                    the bottom of any email or by contacting us directly.
                  </p>
                </section>

                {/* Contact Us */}
                <section className="bg-purple-50 rounded-xl p-6">
                  <h2 className="text-2xl font-black text-gray-900 mb-4">Contact Us</h2>
                  <p className="text-gray-700 mb-4">
                    If you have questions or comments about this Privacy Policy, or wish to exercise your
                    data protection rights, please contact us through our{' '}
                    <a href="/contact" className="text-purple-600 hover:text-purple-800 font-medium underline">
                      Contact Page
                    </a>.
                  </p>
                  <p className="text-gray-700 text-sm">
                    We will respond to your request within 30 days, or sooner if required by applicable law.
                  </p>
                </section>
              </>
            )}
          </div>
        </div>
      </main>

    </>
  );
}
