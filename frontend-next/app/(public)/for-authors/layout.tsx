import type { Metadata } from 'next';

export const metadata: Metadata = {
  title: 'For Authors & Creators | Fresh Motors',
  description: 'Learn how Fresh Motors works with automotive YouTube creators and press release publishers. Our content principles, fair use policy, and collaboration opportunities.',
  openGraph: {
    title: 'For Authors & Creators | Fresh Motors',
    description: 'How Fresh Motors respects content creators — our principles, fair use policy, and collaboration opportunities.',
  },
};

export default function ForAuthorsLayout({ children }: { children: React.ReactNode }) {
  return <>{children}</>;
}
