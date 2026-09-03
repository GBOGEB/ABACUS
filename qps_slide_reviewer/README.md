# QPS Slide Reviewer

An interactive Next.js application for reviewing, rating, and A/B testing the slides of the
**QPS‑3D / QPLANT‑LB** corporate deck. It supports slide browsing, up / neutral / down voting,
starring key slides, group filtering, configurable A/B testing (with ties and free‑text reasons),
and a results dashboard featuring Bradley‑Terry rankings, PCA visualisation and DMAIC KPIs, with
CSV / JSON / YAML export.

## Prerequisites

- **Node.js 20** (LTS)
- **Yarn** (Berry / v4 — the project ships a `.yarnrc.yml`)
- A reachable **PostgreSQL** database

## Setup

1. **Clone the repository** and change into this folder:

   ```bash
   git clone https://github.com/GBOGEB/ABACUS.git
   cd ABACUS/qps_slide_reviewer
   ```

2. **Install dependencies:**

   ```bash
   yarn install
   ```

3. **Configure the environment.** Copy the example env file and fill in your database URL:

   ```bash
   cp .env.example .env
   # then edit .env and set DATABASE_URL=postgresql://USER:PASSWORD@HOST:5432/DATABASE?schema=public
   ```

4. **Push the Prisma schema** to your database:

   ```bash
   yarn prisma db push
   ```

5. **Seed the database** with the 15 slides and their metadata (titles / groups):

   ```bash
   yarn prisma db seed
   ```

6. **Run the development server:**

   ```bash
   yarn dev
   ```

   The app is served at http://localhost:3000.

## Slide images

The slide PNGs are **not** committed to the repository (they are large binary artefacts).
Place them manually in `public/slides/` named `slide-01.png` … `slide-15.png` (one per deck page,
15 in total). See `public/slides/README.md` for details.

## Project structure

| Path | Purpose |
| --- | --- |
| `app/` | Next.js App Router pages (`/`, `/ab-test`, `/results`) and API routes under `app/api/` |
| `components/` | React UI components (slide card / modal, browser, A/B test client, results dashboard, header, footer) |
| `lib/` | `prisma.ts` (client singleton), `analytics.ts` (aggregation), `stats.ts` (Bradley‑Terry, PCA, DMAIC) |
| `prisma/schema.prisma` | Database models (`Slide`, `AbSession`, `AbResult`) |
| `scripts/` | Database seed scripts (`safe-seed.ts`, `seed.ts`) |
| `public/slides/` | Slide images (not committed — see above) |

## Available scripts

- `yarn dev` – start the development server
- `yarn build` – production build
- `yarn start` – run the production build
- `yarn lint` – run ESLint
- `yarn prisma db push` – sync the Prisma schema to the database
- `yarn prisma db seed` – seed slide data

## Branding

Corporate purple headings (`#7030A0`), DM Sans / Plus Jakarta Sans / JetBrains Mono typography,
and an SCK CEN‑style footer (logo bottom‑left, document number, slide number bottom‑right).
See `STYLE_GUIDE.md` for the full design tokens.
