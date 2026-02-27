// Force dynamic rendering for all admin pages
// Admin pages require authentication and should never be statically prerendered
export const dynamic = 'force-dynamic';

export default function AdminTemplate({
    children,
}: {
    children: React.ReactNode;
}) {
    return children;
}
