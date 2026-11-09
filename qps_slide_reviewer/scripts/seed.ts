import { PrismaClient } from '@prisma/client';

const prisma = new PrismaClient();

// Public, identity-neutral placeholders only. The actual slide titles, groups,
// deck identity and offer content are controlled inputs and must not be checked
// into this repository. The public README documents 15 slide image slots.
// This seed provides a working database layout, not reviewed engineering data.
const SLIDE_COUNT = 15;
const GROUP_NAME = 'Unclassified placeholders';

async function main(): Promise<void> {
  console.log('Seeding public slide placeholders (no controlled metadata)...');
  for (let page = 1; page <= SLIDE_COUNT; page += 1) {
    const displayNumber = String(page).padStart(2, '0');
    const imageFilename = `slide-${displayNumber}.png`;
    await prisma.slide.upsert({
      where: { pageNumber: page },
      // A rerun may target a populated/shared review database. Only create
      // missing slots; loaded metadata, custom image paths and votes belong
      // to the existing records and must remain untouched.
      update: {},
      create: {
        pageNumber: page,
        imageFilename,
        title: `Slide ${displayNumber}`,
        groupName: GROUP_NAME,
        starred: false,
        votesUp: 0,
        votesDown: 0,
        votesNeutral: 0,
      },
    });
  }
  console.log(`Seed complete: ${SLIDE_COUNT} slots ensured; existing records preserved.`);
}

main()
  .catch((error: unknown) => {
    console.error('Seed failed:', error);
    process.exitCode = 1;
  })
  .finally(async () => {
    await prisma.$disconnect();
  });
