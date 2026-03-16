import type { Metadata } from 'next';

export const metadata: Metadata = {
  title: 'Compare Cars | Fresh Motors',
  description: 'Side-by-side comparison of electric and hybrid vehicle specifications, performance, range, and pricing. Compare any two cars in our database.',
  openGraph: {
    title: 'Compare Cars | Fresh Motors',
    description: 'Side-by-side comparison of electric and hybrid vehicle specifications, performance, range, and pricing.',
  },
};

export default function CompareLayout({ children }: { children: React.ReactNode }) {
  return <>{children}</>;
}
