export const dynamic = 'force-dynamic';

import { NextResponse } from 'next/server';
import { prisma } from '@/lib/prisma';

export async function GET() {
  try {
    const slides = await prisma.slide.findMany({
      orderBy: { pageNumber: 'asc' },
    });
    return NextResponse.json(slides ?? []);
  } catch (err: any) {
    console.error('GET /api/slides error:', err);
    return NextResponse.json({ error: 'Failed to fetch slides' }, { status: 500 });
  }
}
