import { NextRequest, NextResponse } from 'next/server';
import { revalidatePath, revalidateTag } from 'next/cache';

/**
 * On-demand revalidation endpoint.
 * Called by the backend after article publish/unpublish to instantly
 * refresh the Next.js ISR cache instead of waiting for the revalidate timer.
 *
 * POST /api/revalidate
 * Body: { secret: string, paths?: string[] }
 */
export async function POST(request: NextRequest) {
    try {
        const body = await request.json();

        // Verify secret token (prevents abuse)
        const secret = process.env.REVALIDATION_SECRET || 'freshmotors-revalidate-2026';
        if (body.secret !== secret) {
            return NextResponse.json({ error: 'Invalid secret' }, { status: 401 });
        }

        // Revalidate data cache tags (clears fetch() responses tagged with these)
        revalidateTag('articles', 'max');
        revalidateTag('categories', 'max');

        // Revalidate specified paths (clears route/page cache)
        const paths = body.paths || ['/', '/articles', '/trending'];
        for (const path of paths) {
            revalidatePath(path);
        }

        return NextResponse.json({
            revalidated: true,
            paths,
            tags: ['articles', 'categories'],
            timestamp: new Date().toISOString(),
        });
    } catch (error) {
        return NextResponse.json(
            { error: 'Revalidation failed', detail: String(error) },
            { status: 500 }
        );
    }
}
