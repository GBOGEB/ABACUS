export const dynamic = 'force-dynamic';

import { NextRequest, NextResponse } from 'next/server';
import { buildAnalytics } from '@/lib/analytics';
import { toYaml } from '@/lib/stats';

export async function GET(request: NextRequest) {
  try {
    const format = (request.nextUrl.searchParams.get('format') ?? 'json').toLowerCase();
    const data = await buildAnalytics();
    const stamp = new Date().toISOString().slice(0, 10);

    if (format === 'yaml' || format === 'yml') {
      const body = `# QPS Slide Reviewer export — ${data.meta.docNumber}\n` + toYaml(data);
      return new NextResponse(body, {
        headers: {
          'Content-Type': 'application/x-yaml; charset=utf-8',
          'Content-Disposition': `attachment; filename="qps-slide-review-${stamp}.yaml"`,
        },
      });
    }

    return new NextResponse(JSON.stringify(data, null, 2), {
      headers: {
        'Content-Type': 'application/json; charset=utf-8',
        'Content-Disposition': `attachment; filename="qps-slide-review-${stamp}.json"`,
      },
    });
  } catch (err: any) {
    console.error('GET /api/export error:', err);
    return NextResponse.json({ error: 'Failed to export' }, { status: 500 });
  }
}
