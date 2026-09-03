import { PrismaClient } from '@prisma/client';

const prisma = new PrismaClient();

// Slide metadata extracted from QPS- 3D _DKO.pptx.pdf (SCK CEN/101648634)
const SLIDE_META: { page: number; title: string; group: string }[] = [
  { page: 1, title: 'QPS-LB Offers – Review (title)', group: 'Front matter' },
  { page: 2, title: 'QPLANT-LB 3D Model (ALAT-20260812)', group: 'ALAT 3D model' },
  { page: 3, title: 'QPLANT-LB (Building Integration) – overview', group: 'ALAT 3D model' },
  { page: 4, title: 'QPLANT-LB (Building Integration) – detail', group: 'ALAT 3D model' },
  { page: 5, title: 'Building Integration – QLM-LB wall / multiline interface', group: 'ALAT 3D model' },
  { page: 6, title: 'Building Integration – wall openings', group: 'ALAT 3D model' },
  { page: 7, title: 'Building Integration – CCB height discrepancy', group: 'ALAT 3D model' },
  { page: 8, title: 'Building Integration – structural interference', group: 'ALAT 3D model' },
  { page: 9, title: 'ALAT Compliancy to Requirements (1/2)', group: 'Compliance tables' },
  { page: 10, title: 'ALAT Compliancy to Requirements (2/2)', group: 'Compliance tables' },
  { page: 11, title: 'QPLANT-LB 2D Drawings (LKT-20260812)', group: 'LKT 2D drawings' },
  { page: 12, title: 'QRB-LB & WCS-LB Rooms', group: 'LKT 2D drawings' },
  { page: 13, title: 'LKT Compliancy to Requirements (1/2)', group: 'Compliance tables' },
  { page: 14, title: 'LKT Compliancy to Requirements (2/2)', group: 'Compliance tables' },
  { page: 15, title: 'Copyright / closure', group: 'Front matter' },
];

async function main() {
  console.log('Seeding slides...');

  for (const meta of SLIDE_META) {
    const filename = `slide-${String(meta.page).padStart(2, '0')}.png`;
    await prisma.slide.upsert({
      where: { pageNumber: meta.page },
      update: { imageFilename: filename, title: meta.title, groupName: meta.group },
      create: {
        pageNumber: meta.page,
        imageFilename: filename,
        title: meta.title,
        groupName: meta.group,
        starred: false,
        votesUp: 0,
        votesDown: 0,
        votesNeutral: 0,
      },
    });
    console.log(`  Slide ${meta.page}: ${filename} [${meta.group}]`);
  }

  console.log('Seeding complete.');
}

main()
  .catch((e: any) => {
    console.error('Seed failed:', e);
    process.exit(1);
  })
  .finally(async () => {
    await prisma.$disconnect();
  });
