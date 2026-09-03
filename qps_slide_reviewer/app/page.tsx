import { Header } from '@/components/header';
import { Footer } from '@/components/footer';
import { SlideBrowserClient } from '@/components/slide-browser-client';

export default function HomePage() {
  return (
    <div className="flex min-h-screen flex-col">
      <Header />
      <main className="flex-1">
        <SlideBrowserClient />
      </main>
      <Footer />
    </div>
  );
}
