import Header from '@/components/public/Header';
import Footer from '@/components/public/Footer';
import { Users, Target, Award, TrendingUp } from 'lucide-react';

export const metadata = {
  title: 'About Us - Fresh Motors',
  description: 'Learn more about Fresh Motors - your trusted source for automotive news and reviews.',
};

export default function AboutPage() {
  return (
    <>
      <Header />
      
      <main className="flex-1 bg-gray-50">
        {/* Hero Section */}
        <div className="bg-gradient-to-r from-slate-900 via-purple-900 to-gray-900 text-white py-20">
          <div className="container mx-auto px-4 text-center">
            <h1 className="text-4xl md:text-5xl font-black mb-4">About Fresh Motors</h1>
            <p className="text-xl text-gray-300 max-w-3xl mx-auto">
              Your trusted source for the latest automotive news, in-depth reviews, and expert insights.
            </p>
          </div>
        </div>

        <div className="container mx-auto px-4 py-12">
          {/* Our Story */}
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

          {/* Our Values */}
          <section className="mb-8">
            <h2 className="text-3xl font-black text-gray-900 mb-6 text-center">What We Stand For</h2>
            <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-6">
              <div className="bg-white rounded-xl shadow-md p-6 text-center hover:shadow-xl transition-shadow">
                <div className="bg-purple-100 w-16 h-16 rounded-full flex items-center justify-center mx-auto mb-4">
                  <Target className="text-purple-600" size={32} />
                </div>
                <h3 className="text-xl font-bold text-gray-900 mb-2">Accuracy</h3>
                <p className="text-gray-600">
                  We verify every fact and double-check our sources to ensure you get reliable information.
                </p>
              </div>

              <div className="bg-white rounded-xl shadow-md p-6 text-center hover:shadow-xl transition-shadow">
                <div className="bg-indigo-100 w-16 h-16 rounded-full flex items-center justify-center mx-auto mb-4">
                  <TrendingUp className="text-indigo-600" size={32} />
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

          {/* What We Cover */}
          <section className="bg-white rounded-2xl shadow-lg p-8 md:p-12">
            <h2 className="text-3xl font-black text-gray-900 mb-6">What We Cover</h2>
            <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
              <div>
                <h3 className="text-xl font-bold text-purple-600 mb-3">Latest News</h3>
                <p className="text-gray-700 mb-4">
                  Breaking stories from the automotive industry, including new model announcements, 
                  technological breakthroughs, and industry trends.
                </p>
              </div>
              <div>
                <h3 className="text-xl font-bold text-purple-600 mb-3">In-Depth Reviews</h3>
                <p className="text-gray-700 mb-4">
                  Comprehensive reviews of the latest vehicles, covering performance, features, 
                  safety, and value for money.
                </p>
              </div>
              <div>
                <h3 className="text-xl font-bold text-purple-600 mb-3">Electric Vehicles</h3>
                <p className="text-gray-700 mb-4">
                  Dedicated coverage of the EV revolution, including battery technology, 
                  charging infrastructure, and sustainability.
                </p>
              </div>
              <div>
                <h3 className="text-xl font-bold text-purple-600 mb-3">Expert Analysis</h3>
                <p className="text-gray-700 mb-4">
                  Insights from industry experts, market analysis, and predictions about 
                  the future of transportation.
                </p>
              </div>
            </div>
          </section>
        </div>
      </main>
      
      <Footer />
    </>
  );
}
