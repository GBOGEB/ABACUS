import { Header } from '@/components/header';
import { Footer } from '@/components/footer';
import { ResultsClient } from '@/components/results-client';

export default function ResultsPage() {
  return (
    <div className="flex min-h-screen flex-col">
      <Header />
      <main className="flex-1">
        <ResultsClient />
      </main>
      <Footer />
    </div>
  );
}
