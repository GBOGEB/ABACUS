export const dynamic = 'force-dynamic';

import { NextResponse } from 'next/server';
import { buildAnalytics } from '@/lib/analytics';

function csvCell(v: unknown): string {
  if (v === null || v === undefined) return '';
  const s = String(v);
  return /[",\n]/.test(s) ? `"${s.replace(/"/g, '""')}"` : s;
}

export async function GET() {
  try {
    const data = await buildAnalytics();
    const header = [
      'Slide', 'Title', 'Group', 'Starred', 'Votes Up', 'Votes Down', 'Votes Neutral', 'Net Votes',
      'A/B Wins', 'A/B Losses', 'A/B Ties', 'Win Rate', 'BT Strength', 'BT Log Strength', 'BT Std Error', 'BT Rank', 'PC1', 'PC2',
    ];
    const rows = data.slides.map((s) => [
      s.pageNumber, s.title, s.groupName, s.starred ? 'Yes' : 'No', s.votesUp, s.votesDown, s.votesNeutral, s.netVotes,
      s.abWins, s.abLosses, s.abTies, s.winRate.toFixed(3), s.btStrength.toFixed(4), s.btLogStrength.toFixed(4),
      s.btStdError === null ? '' : s.btStdError.toFixed(4), s.btRank, s.pc1.toFixed(4), s.pc2.toFixed(4),
    ].map(csvCell).join(','));

    const csv = [header.join(','), ...rows].join('\n');
    return new NextResponse(csv, {
      headers: {
        'Content-Type': 'text/csv; charset=utf-8',
        'Content-Disposition': 'attachment; filename="qps-slide-results.csv"',
      },
    });
  } catch (err: any) {
    console.error('GET /api/export-csv error:', err);
    return NextResponse.json({ error: 'Failed to export' }, { status: 500 });
  }
}
