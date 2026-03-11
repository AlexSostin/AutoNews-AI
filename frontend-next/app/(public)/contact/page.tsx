import { Metadata } from 'next';
import { Mail, MapPin, Phone } from 'lucide-react';
import { getApiUrl } from '@/lib/api';
import ContactForm from './ContactForm';

export const metadata: Metadata = {
  title: 'Contact Us | Fresh Motors',
  description: 'Get in touch with Fresh Motors. Have a question about a vehicle, feedback on our content, or business inquiries? We\'d love to hear from you.',
};

interface SiteSettings {
  contact_email: string;
  contact_phone: string;
  contact_phone_enabled: boolean;
  contact_address: string;
  contact_address_enabled: boolean;
  support_email: string;
  business_email: string;
  contact_page_title: string;
  contact_page_subtitle: string;
  contact_page_enabled: boolean;
}

async function getSettings(): Promise<SiteSettings | null> {
  try {
    const apiUrl = getApiUrl();
    const res = await fetch(`${apiUrl}/settings/`, {
      next: { revalidate: 300 },
    });
    if (res.ok) return res.json();
  } catch {}
  return null;
}

export default async function ContactPage() {
  const settings = await getSettings();

  // Safely extract settings
  const contactEmail = settings?.contact_email || 'info@freshmotors.net';
  const hasPhone = !!(settings?.contact_phone && settings?.contact_phone_enabled);
  const hasAddress = !!(settings?.contact_address && settings?.contact_address_enabled);
  const hasSupportEmail = settings?.support_email;
  const hasBusinessEmail = settings?.business_email;

  return (
    <>
      <main className="flex-1 bg-gray-50">
        {/* Hero Section */}
        <div className="bg-gradient-to-r from-slate-900 via-purple-900 to-gray-900 text-white py-20">
          <div className="container mx-auto px-4 text-center">
            <h1 className="text-4xl md:text-5xl font-black mb-4">
              {settings?.contact_page_title || 'Contact Us'}
            </h1>
            <p className="text-xl text-gray-300 max-w-3xl mx-auto">
              {settings?.contact_page_subtitle || "Have a question, suggestion, or just want to say hello? We'd love to hear from you!"}
            </p>
          </div>
        </div>

        <div className="container mx-auto px-4 py-12 max-w-6xl">
          <div className="bg-white rounded-3xl shadow-xl overflow-hidden flex flex-col lg:flex-row border border-gray-100">

            {/* Contact Information Sidebar */}
            <div className="lg:w-1/3 bg-gradient-to-br from-indigo-900 via-purple-900 to-slate-900 p-8 sm:p-12 text-white flex flex-col justify-between">
              <div>
                <h2 className="text-3xl font-black mb-6">Get in Touch</h2>
                <p className="text-purple-100/80 mb-10 leading-relaxed font-medium">
                  We&apos;re here to help! Whether you have questions about a vehicle, feedback on our content, or business inquiries, reach out using any method below.
                </p>

                <div className="space-y-8">
                  {/* Email */}
                  <div className="flex items-start gap-4 group">
                    <div className="bg-white/10 p-3 rounded-2xl group-hover:bg-white/20 transition-colors">
                      <Mail className="text-purple-300" size={24} />
                    </div>
                    <div>
                      <p className="text-xs font-black uppercase tracking-widest text-purple-300/80 mb-1">Email Us</p>
                      <a href={`mailto:${contactEmail}`} className="text-lg font-bold hover:text-purple-300 transition-colors">
                        {contactEmail}
                      </a>
                      {hasSupportEmail && (
                        <p className="text-sm text-purple-200/60 mt-0.5">Support: {settings?.support_email}</p>
                      )}
                    </div>
                  </div>

                  {/* Phone */}
                  {hasPhone && settings?.contact_phone && (
                    <div className="flex items-start gap-4 group">
                      <div className="bg-white/10 p-3 rounded-2xl group-hover:bg-white/20 transition-colors">
                        <Phone className="text-purple-300" size={24} />
                      </div>
                      <div>
                        <p className="text-xs font-black uppercase tracking-widest text-purple-300/80 mb-1">Call Us</p>
                        <a href={`tel:${settings.contact_phone.replace(/\s/g, '')}`} className="text-lg font-bold hover:text-purple-300 transition-colors">
                          {settings.contact_phone}
                        </a>
                      </div>
                    </div>
                  )}

                  {/* Address */}
                  {hasAddress && settings?.contact_address && (
                    <div className="flex items-start gap-4 group">
                      <div className="bg-white/10 p-3 rounded-2xl group-hover:bg-white/20 transition-colors">
                        <MapPin className="text-purple-300" size={24} />
                      </div>
                      <div>
                        <p className="text-xs font-black uppercase tracking-widest text-purple-300/80 mb-1">Visit Us</p>
                        <div className="text-base font-medium text-purple-50 line-clamp-3">
                          {settings.contact_address.split('\n').map((line: string, idx: number) => (
                            <span key={idx} className="block">{line}</span>
                          ))}
                        </div>
                      </div>
                    </div>
                  )}
                </div>
              </div>

              {/* Business Inquiries Box */}
              {hasBusinessEmail && settings?.business_email && (
                <div className="mt-12 p-6 bg-white/5 border border-white/10 rounded-2xl">
                  <p className="text-xs font-black uppercase tracking-widest text-indigo-300 mb-2">Business Inquiries</p>
                  <p className="text-sm text-indigo-100/70 mb-3">For partnerships or press, please email us directly:</p>
                  <a href={`mailto:${settings.business_email}`} className="text-sm font-black text-white hover:text-indigo-300 transition-colors border-b border-indigo-500/30 pb-0.5">
                    {settings.business_email}
                  </a>
                </div>
              )}
            </div>

            {/* Contact Form — Client Component */}
            <ContactForm />
          </div>
        </div>
      </main>
    </>
  );
}
