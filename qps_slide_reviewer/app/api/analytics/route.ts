export const dynamic = 'force-dynamic';

import { NextResponse } from 'next/server';
import { buildAnalytics } from '@/lib/analytics';

export async function GET() {
  try {
    const data = await buildAnalytics();
    return NextResponse.json(data);
  } catch (err: any) {
    console.error('GET /api/analytics error:', err);
    return NextResponse.json({ error: 'Failed to build analytics' }, { status: 500 });
  }
}
