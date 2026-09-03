import { Header } from '@/components/header';
import { Footer } from '@/components/footer';
import { AbTestClient } from '@/components/ab-test-client';

export default function AbTestPage() {
  return (
    <div className="flex min-h-screen flex-col">
      <Header />
      <main className="flex-1">
        <AbTestClient />
      </main>
      <Footer />
    </div>
  );
}
