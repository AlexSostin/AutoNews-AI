'use client';

import { useState, useEffect } from 'react';
import { FileText, AlertCircle, Scale, UserCheck, Loader2 } from 'lucide-react';
import { getApiUrl } from '@/lib/api';

interface SiteSettings {
  terms_page_title: string;
  terms_page_content: string;
  terms_page_enabled: boolean;
}

export default function TermsPage() {
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

  const pageTitle = settings?.terms_page_title || 'Terms of Service';
  const pageContent = settings?.terms_page_content || '';
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
            <FileText className="mx-auto mb-4 text-purple-300" size={48} />
            <h1 className="text-4xl md:text-5xl font-black mb-4">{pageTitle}</h1>
            <p className="text-lg text-gray-300 max-w-2xl mx-auto">
              Last Updated: February 13, 2026
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
                    Welcome to Fresh Motors. These Terms of Service ("Terms") govern your access to and use of our
                    website, services, and content. By accessing or using Fresh Motors, you agree to be bound by
                    these Terms. If you do not agree to these Terms, please do not use our website.
                  </p>
                  <div className="bg-amber-50 border border-amber-200 rounded-lg p-4 flex gap-3">
                    <AlertCircle className="text-amber-600 flex-shrink-0 mt-1" size={20} />
                    <p className="text-sm text-amber-900">
                      <strong>Important:</strong> Please read these Terms carefully before using our services.
                      Your continued use of the website constitutes acceptance of these Terms.
                    </p>
                  </div>
                </section>

                {/* Acceptance of Terms */}
                <section className="mb-10">
                  <div className="flex items-center gap-3 mb-4">
                    <div className="bg-purple-100 p-2 rounded-lg">
                      <UserCheck className="text-purple-600" size={24} />
                    </div>
                    <h2 className="text-2xl font-black text-gray-900">Acceptance of Terms</h2>
                  </div>
                  <p className="text-gray-700">
                    By accessing and using this website, you accept and agree to be bound by these Terms and
                    our Privacy Policy. If you do not agree to these Terms, you are not authorized to use our
                    website and should discontinue use immediately.
                  </p>
                </section>

                {/* Use of Website */}
                <section className="mb-10">
                  <h2 className="text-2xl font-black text-gray-900 mb-4">Use of Website</h2>

                  <h3 className="text-lg font-bold text-gray-900 mb-2">Permitted Use</h3>
                  <p className="text-gray-700 mb-4">
                    You may use our website for lawful purposes only. You agree not to:
                  </p>
                  <ul className="list-disc list-inside text-gray-700 mb-4 space-y-1 ml-4">
                    <li>Violate any applicable laws or regulations</li>
                    <li>Infringe on the intellectual property rights of others</li>
                    <li>Transmit any harmful code, viruses, or malware</li>
                    <li>Attempt to gain unauthorized access to our systems</li>
                    <li>Harass, abuse, or harm other users</li>
                    <li>Use automated systems (bots, scrapers) without permission</li>
                  </ul>
                </section>

                {/* Intellectual Property */}
                <section className="mb-10">
                  <div className="flex items-center gap-3 mb-4">
                    <div className="bg-indigo-100 p-2 rounded-lg">
                      <Scale className="text-indigo-600" size={24} />
                    </div>
                    <h2 className="text-2xl font-black text-gray-900">Intellectual Property Rights</h2>
                  </div>

                  <h3 className="text-lg font-bold text-gray-900 mb-2">Our Content</h3>
                  <p className="text-gray-700 mb-4">
                    All content on this website, including but not limited to text, images, graphics, logos,
                    videos, and software, is the property of Fresh Motors or its content suppliers and is protected
                    by copyright, trademark, and other intellectual property laws.
                  </p>

                  <h3 className="text-lg font-bold text-gray-900 mb-2">Limited License</h3>
                  <p className="text-gray-700 mb-4">
                    We grant you a limited, non-exclusive, non-transferable license to access and use our website
                    for personal, non-commercial purposes. You may not:
                  </p>
                  <ul className="list-disc list-inside text-gray-700 space-y-1 ml-4">
                    <li>Reproduce, distribute, or publicly display our content without permission</li>
                    <li>Modify or create derivative works from our content</li>
                    <li>Use our content for commercial purposes without authorization</li>
                  </ul>
                </section>

                {/* User Content */}
                <section className="mb-10">
                  <h2 className="text-2xl font-black text-gray-900 mb-4">User-Generated Content</h2>
                  <p className="text-gray-700 mb-4">
                    If you submit comments, reviews, or other content to our website, you:
                  </p>
                  <ul className="list-disc list-inside text-gray-700 space-y-2 ml-4">
                    <li>Grant us a non-exclusive, worldwide, royalty-free license to use, reproduce, and display your content</li>
                    <li>Represent that you own or have rights to the content you submit</li>
                    <li>Agree that your content does not violate any laws or infringe on third-party rights</li>
                    <li>Understand that we may remove any content that violates these Terms</li>
                  </ul>
                </section>

                {/* Third-Party Links */}
                <section className="mb-10">
                  <h2 className="text-2xl font-black text-gray-900 mb-4">Third-Party Links and Services</h2>
                  <p className="text-gray-700">
                    Our website may contain links to third-party websites or services that are not owned or
                    controlled by Fresh Motors. We have no control over and assume no responsibility for the content,
                    privacy policies, or practices of any third-party websites or services. You acknowledge and
                    agree that Fresh Motors shall not be liable for any damage or loss caused by your use of any
                    third-party content or services.
                  </p>
                </section>

                {/* Disclaimer */}
                <section className="mb-10">
                  <h2 className="text-2xl font-black text-gray-900 mb-4">Disclaimer of Warranties</h2>
                  <p className="text-gray-700 mb-4">
                    Our website and content are provided on an "AS IS" and "AS AVAILABLE" basis. We make no
                    warranties or representations about the accuracy, reliability, completeness, or timeliness
                    of the content.
                  </p>
                  <div className="bg-gray-100 rounded-lg p-4">
                    <p className="text-sm text-gray-700 font-medium uppercase mb-2">Disclaimer:</p>
                    <p className="text-sm text-gray-600">
                      TO THE FULLEST EXTENT PERMITTED BY LAW, FRESH MOTORS DISCLAIMS ALL WARRANTIES, EXPRESS OR
                      IMPLIED, INCLUDING WARRANTIES OF MERCHANTABILITY, FITNESS FOR A PARTICULAR PURPOSE, AND
                      NON-INFRINGEMENT.
                    </p>
                  </div>
                </section>

                {/* Limitation of Liability */}
                <section className="mb-10">
                  <h2 className="text-2xl font-black text-gray-900 mb-4">Limitation of Liability</h2>
                  <p className="text-gray-700">
                    To the maximum extent permitted by law, Fresh Motors and its officers, directors, employees,
                    and agents shall not be liable for any indirect, incidental, special, consequential, or
                    punitive damages, including but not limited to loss of profits, data, or other intangible
                    losses resulting from your use or inability to use our website.
                  </p>
                </section>

                {/* Indemnification */}
                <section className="mb-10">
                  <h2 className="text-2xl font-black text-gray-900 mb-4">Indemnification</h2>
                  <p className="text-gray-700">
                    You agree to indemnify, defend, and hold harmless Fresh Motors and its affiliates from any claims,
                    liabilities, damages, losses, and expenses (including reasonable attorneys' fees) arising out
                    of or in any way connected with your access to or use of our website or your violation of
                    these Terms.
                  </p>
                </section>

                {/* Changes to Terms */}
                <section className="mb-10">
                  <h2 className="text-2xl font-black text-gray-900 mb-4">Changes to Terms</h2>
                  <p className="text-gray-700">
                    We reserve the right to modify or replace these Terms at any time at our sole discretion.
                    If we make material changes, we will provide notice by posting the updated Terms on this
                    page with a new "Last Updated" date. Your continued use of the website after any changes
                    constitutes acceptance of the new Terms.
                  </p>
                </section>

                {/* Governing Law */}
                <section className="mb-10">
                  <h2 className="text-2xl font-black text-gray-900 mb-4">Governing Law</h2>
                  <p className="text-gray-700 mb-4">
                    These Terms shall be governed by and construed in accordance with the applicable laws of
                    your jurisdiction. Any disputes arising from these Terms or your use of the website will
                    be resolved in accordance with the laws applicable to your place of residence, to the
                    extent required by local consumer protection laws.
                  </p>
                  <p className="text-gray-700">
                    For users outside your local jurisdiction, you agree that any disputes will be resolved
                    through good-faith negotiation or, if necessary, through binding arbitration in accordance
                    with internationally recognized arbitration rules.
                  </p>
                </section>

                {/* Age Requirements */}
                <section className="mb-10">
                  <h2 className="text-2xl font-black text-gray-900 mb-4">Age Requirements</h2>
                  <p className="text-gray-700">
                    You must be at least 16 years of age to use this website. By using Fresh Motors, you represent
                    and warrant that you meet this age requirement. If you are under 16, please do not use our
                    website or submit any personal information.
                  </p>
                </section>

                {/* International Users */}
                <section className="mb-10">
                  <h2 className="text-2xl font-black text-gray-900 mb-4">International Users</h2>
                  <p className="text-gray-700">
                    Fresh Motors is accessible worldwide. If you access the website from outside of our primary
                    operating region, you do so at your own initiative and are responsible for compliance with
                    local laws. Nothing in these Terms excludes or limits any consumer rights that cannot be
                    excluded or limited under the laws of your country of residence.
                  </p>
                </section>

                {/* Contact */}
                <section className="bg-purple-50 rounded-xl p-6">
                  <h2 className="text-2xl font-black text-gray-900 mb-4">Contact Us</h2>
                  <p className="text-gray-700 mb-4">
                    If you have any questions about these Terms of Service, please contact us through our{' '}
                    <a href="/contact" className="text-purple-600 hover:text-purple-800 font-medium underline">
                      Contact Page
                    </a>.
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
