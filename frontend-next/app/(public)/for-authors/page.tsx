'use client';

import {
    Youtube,
    Trash2,
    Handshake,
    Lock,
    FileText,
    Mail,
    ChevronRight,
    Info
} from 'lucide-react';
import Link from 'next/link';

export default function ForAuthorsPage() {
    const principles = [
        {
            icon: <Youtube className="text-red-600" size={32} />,
            title: "Official YouTube Embeds",
            description: "We only use the official YouTube player. This means views on our site count towards your YouTube stats, and all channel ads are displayed correctly."
        },
        {
            icon: <Lock className="text-indigo-600" size={32} />,
            title: "No Text Copying",
            description: "We never copy the original text of your descriptions or subtitles in their entirety. Our primary goal is to create unique, high-value supplementary content."
        },
        {
            icon: <FileText className="text-green-600" size={32} />,
            title: "Smart Summaries",
            description: "We generate concise text summaries of videos for user convenience, helping them quickly find relevant information and click through to watch the original."
        },
        {
            icon: <Trash2 className="text-orange-600" size={32} />,
            title: "Easy Removal",
            description: "We respect your content rights. We are ready to remove or modify your publication page immediately upon request."
        },
        {
            icon: <Handshake className="text-purple-600" size={32} />,
            title: "Collaboration",
            description: "We are open to collaboration! We can highlight your channel or add direct links to your social media if you'd like to work with us."
        }
    ];

    return (
        <div className="min-h-screen bg-gray-50 pb-20">
            {/* Hero Header */}
            <div className="bg-gray-900 text-white py-16 sm:py-24">
                <div className="container mx-auto px-4 text-center">
                    <h1 className="text-4xl sm:text-5xl md:text-6xl font-black mb-6 bg-gradient-to-r from-indigo-400 to-purple-400 bg-clip-text text-transparent">
                        Fresh Motors — For Authors
                    </h1>
                    <p className="text-xl text-gray-400 max-w-2xl mx-auto leading-relaxed">
                        We are building a platform that helps creators reach new audiences
                        while respecting intellectual property and YouTube guidelines.
                    </p>
                </div>
            </div>

            <div className="container mx-auto px-4 -mt-12">
                {/* Main Principles Grid */}
                <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6 mb-16">
                    {principles.map((p, i) => (
                        <div key={i} className="bg-white rounded-3xl p-8 shadow-xl shadow-gray-200/50 border border-gray-100 hover:scale-[1.02] transition-transform duration-300">
                            <div className="bg-gray-50 w-16 h-16 rounded-2xl flex items-center justify-center mb-6">
                                {p.icon}
                            </div>
                            <h3 className="text-xl font-bold text-gray-900 mb-3">{p.title}</h3>
                            <p className="text-gray-600 leading-relaxed text-sm lg:text-base">
                                {p.description}
                            </p>
                        </div>
                    ))}

                    {/* Contact Card */}
                    <div className="bg-indigo-600 rounded-3xl p-8 shadow-xl shadow-indigo-200 text-white md:col-span-2 lg:col-span-1 flex flex-col justify-between">
                        <div>
                            <div className="bg-white/20 w-16 h-16 rounded-2xl flex items-center justify-center mb-6">
                                <Mail size={32} />
                            </div>
                            <h3 className="text-xl font-bold mb-3">Contact Us</h3>
                            <p className="text-indigo-100 mb-6 leading-relaxed">
                                Have questions or partnership proposals? Email us, we respond within 24 hours.
                            </p>
                        </div>
                        <a
                            href="mailto:info@freshmotors.net"
                            className="inline-flex items-center justify-center gap-2 bg-white text-indigo-600 font-bold py-3 px-6 rounded-xl hover:bg-gray-100 transition-colors"
                        >
                            info@freshmotors.net
                            <ChevronRight size={18} />
                        </a>
                    </div>
                </div>

                {/* Legal Disclaimer Box */}
                <div className="max-w-4xl mx-auto bg-white rounded-3xl border-2 border-dashed border-gray-200 p-8 sm:p-12">
                    <div className="flex items-center gap-3 mb-6 text-gray-400">
                        <Info size={24} />
                        <span className="font-bold uppercase tracking-wider text-sm">Transparency Policy</span>
                    </div>
                    <p className="text-gray-700 leading-relaxed mb-6 italic">
                        "We believe content aggregation should be beneficial for those who create it.
                        Fresh Motors is not a replacement for your channel, but a bridge to it. Our
                        automation is designed to help users quickly grasp the topic and immediately
                        head to the original source."
                    </p>
                    <div className="flex flex-wrap gap-4">
                        <Link
                            href="/articles"
                            className="font-bold text-indigo-600 hover:text-indigo-800 transition-colors flex items-center gap-2"
                        >
                            Browse Articles
                            <ChevronRight size={18} />
                        </Link>
                    </div>
                </div>
            </div>
        </div>
    );
}
