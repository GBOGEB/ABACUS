export const dynamic = 'force-dynamic';

import { NextResponse } from 'next/server';
import { prisma } from '@/lib/prisma';

export async function POST(
  _request: Request,
  { params }: { params: Promise<{ id: string }> }
) {
  try {
    const { id } = await params;
    const slideId = parseInt(id, 10);
    if (isNaN(slideId)) {
      return NextResponse.json({ error: 'Invalid id' }, { status: 400 });
    }
    const current = await prisma.slide.findUnique({ where: { id: slideId } });
    if (!current) {
      return NextResponse.json({ error: 'Not found' }, { status: 404 });
    }
    const updated = await prisma.slide.update({
      where: { id: slideId },
      data: { starred: !current.starred },
    });
    return NextResponse.json(updated);
  } catch (err: any) {
    console.error('POST /api/slides/[id]/star error:', err);
    return NextResponse.json({ error: 'Failed to toggle star' }, { status: 500 });
  }
}
