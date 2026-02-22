'use client';

import { useState, useEffect } from 'react';
import { Users, Target, Award, TrendingUp, Loader2 } from 'lucide-react';
import { getApiUrl } from '@/lib/api';

interface SiteSettings {
  about_page_title: string;
  about_page_content: string;
  about_page_enabled: boolean;
}

// Default content if API doesn't provide custom content
const defaultContent = `
<h2>Our Story</h2>
<p>Founded with a passion for automobiles and a commitment to delivering accurate, timely information, 
Fresh Motors has grown into a comprehensive platform for car enthusiasts, industry professionals, 
and everyday drivers alike.</p>
<p>We believe that staying informed about the automotive world should be accessible, engaging, 
and reliable. From breaking news about the latest electric vehicles to detailed reviews of 
classic sports cars, we cover it all with expertise and enthusiasm.</p>
<p>Our team of automotive journalists and industry experts work tirelessly to bring you the most 
relevant and interesting content, helping you make informed decisions about your next vehicle 
purchase or simply stay connected with the ever-evolving world of automobiles.</p>
`;

export default function AboutPage() {
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

  // Get content - use API content if available, otherwise use default
  const pageTitle = settings?.about_page_title || 'About Fresh Motors';
  const pageContent = settings?.about_page_content || '';
  const hasCustomContent = pageContent.trim().length > 0;

  if (loading) {
    return (
      <main className="flex-1 bg-gray-50 flex items-center justify-center min-h-[60vh]">
        <Loader2 className="animate-spin text-brand-600" size={48} />
      </main>
    );
  }

  return (
    <>

      <main className="flex-1 bg-gray-50">
        {/* Hero Section */}
        <div className="bg-gradient-to-r from-slate-900 via-brand-900 to-gray-900 text-white py-20">
          <div className="container mx-auto px-4 text-center">
            <h1 className="text-4xl md:text-5xl font-black mb-4">{pageTitle}</h1>
            <p className="text-xl text-gray-300 max-w-3xl mx-auto">
              Your trusted source for the latest automotive news, in-depth reviews, and expert insights.
            </p>
          </div>
        </div>

        <div className="container mx-auto px-4 py-12">
          {/* Custom Content from Admin */}
          {hasCustomContent ? (
            <section className="bg-white rounded-2xl shadow-lg p-8 md:p-12 mb-8">
              <div
                className="prose prose-lg max-w-none text-gray-700"
                dangerouslySetInnerHTML={{ __html: pageContent }}
              />
            </section>
          ) : (
            <>
              {/* Default Our Story */}
              <section className="bg-white rounded-2xl shadow-lg p-8 md:p-12 mb-8">
                <h2 className="text-3xl font-black text-gray-900 mb-6">Our Story</h2>
                <div className="prose prose-lg max-w-none text-gray-700">
                  <p className="mb-4">
                    Founded with a passion for automobiles and a commitment to delivering accurate, timely information,
                    Fresh Motors has grown into a comprehensive platform for car enthusiasts, industry professionals,
                    and everyday drivers alike.
                  </p>
                  <p className="mb-4">
                    We believe that staying informed about the automotive world should be accessible, engaging,
                    and reliable. From breaking news about the latest electric vehicles to detailed reviews of
                    classic sports cars, we cover it all with expertise and enthusiasm.
                  </p>
                  <p>
                    Our team of automotive journalists and industry experts work tirelessly to bring you the most
                    relevant and interesting content, helping you make informed decisions about your next vehicle
                    purchase or simply stay connected with the ever-evolving world of automobiles.
                  </p>
                </div>
              </section>

              {/* Default Our Values */}
              <section className="mb-8">
                <h2 className="text-3xl font-black text-gray-900 mb-6 text-center">What We Stand For</h2>
                <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-6">
                  <div className="bg-white rounded-xl shadow-md p-6 text-center hover:shadow-xl transition-shadow">
                    <div className="bg-brand-100 w-16 h-16 rounded-full flex items-center justify-center mx-auto mb-4">
                      <Target className="text-brand-600" size={32} />
                    </div>
                    <h3 className="text-xl font-bold text-gray-900 mb-2">Accuracy</h3>
                    <p className="text-gray-600">
                      We verify every fact and double-check our sources to ensure you get reliable information.
                    </p>
                  </div>

                  <div className="bg-white rounded-xl shadow-md p-6 text-center hover:shadow-xl transition-shadow">
                    <div className="bg-brand-100 w-16 h-16 rounded-full flex items-center justify-center mx-auto mb-4">
                      <TrendingUp className="text-brand-600" size={32} />
                    </div>
                    <h3 className="text-xl font-bold text-gray-900 mb-2">Innovation</h3>
                    <p className="text-gray-600">
                      We stay ahead of automotive trends and emerging technologies to keep you informed.
                    </p>
                  </div>

                  <div className="bg-white rounded-xl shadow-md p-6 text-center hover:shadow-xl transition-shadow">
                    <div className="bg-blue-100 w-16 h-16 rounded-full flex items-center justify-center mx-auto mb-4">
                      <Award className="text-blue-600" size={32} />
                    </div>
                    <h3 className="text-xl font-bold text-gray-900 mb-2">Excellence</h3>
                    <p className="text-gray-600">
                      We strive for excellence in every article, review, and piece of content we publish.
                    </p>
                  </div>

                  <div className="bg-white rounded-xl shadow-md p-6 text-center hover:shadow-xl transition-shadow">
                    <div className="bg-green-100 w-16 h-16 rounded-full flex items-center justify-center mx-auto mb-4">
                      <Users className="text-green-600" size={32} />
                    </div>
                    <h3 className="text-xl font-bold text-gray-900 mb-2">Community</h3>
                    <p className="text-gray-600">
                      We foster a community of car enthusiasts who share our passion for automobiles.
                    </p>
                  </div>
                </div>
              </section>

              {/* Default What We Cover */}
              <section className="bg-white rounded-2xl shadow-lg p-8 md:p-12">
                <h2 className="text-3xl font-black text-gray-900 mb-6">What We Cover</h2>
                <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
                  <div>
                    <h3 className="text-xl font-bold text-brand-600 mb-3">Latest News</h3>
                    <p className="text-gray-700 mb-4">
                      Breaking stories from the automotive industry, including new model announcements,
                      technological breakthroughs, and industry trends.
                    </p>
                  </div>
                  <div>
                    <h3 className="text-xl font-bold text-brand-600 mb-3">In-Depth Reviews</h3>
                    <p className="text-gray-700 mb-4">
                      Comprehensive reviews of the latest vehicles, covering performance, features,
                      safety, and value for money.
                    </p>
                  </div>
                  <div>
                    <h3 className="text-xl font-bold text-brand-600 mb-3">Electric Vehicles</h3>
                    <p className="text-gray-700 mb-4">
                      Dedicated coverage of the EV revolution, including battery technology,
                      charging infrastructure, and sustainability.
                    </p>
                  </div>
                  <div>
                    <h3 className="text-xl font-bold text-brand-600 mb-3">Expert Analysis</h3>
                    <p className="text-gray-700 mb-4">
                      Insights from industry experts, market analysis, and predictions about
                      the future of transportation.
                    </p>
                  </div>
                </div>
              </section>
            </>
          )}
        </div>
      </main>

    </>
  );
}
