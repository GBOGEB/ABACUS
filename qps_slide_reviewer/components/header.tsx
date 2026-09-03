'use client';

import Link from 'next/link';
import { usePathname } from 'next/navigation';
import { LayoutGrid, GitCompare, BarChart3 } from 'lucide-react';
import { cn } from '@/lib/utils';

const navItems = [
  { href: '/', label: 'Browser', icon: LayoutGrid },
  { href: '/ab-test', label: 'A/B Test', icon: GitCompare },
  { href: '/results', label: 'Results', icon: BarChart3 },
];

export function Header() {
  const pathname = usePathname();

  return (
    <header className="sticky top-0 z-50 w-full border-b bg-background/80 backdrop-blur-md">
      <div className="mx-auto flex h-16 max-w-[1200px] items-center justify-between px-4">
        <Link href="/" className="flex items-center gap-2">
          <div className="flex h-9 w-9 items-center justify-center rounded-lg bg-primary text-primary-foreground font-display font-bold text-sm">
            QPS
          </div>
          <span className="font-display text-lg font-bold tracking-tight text-primary">
            Slide Reviewer
          </span>
        </Link>
        <nav className="flex items-center gap-1">
          {navItems?.map((item: typeof navItems[number]) => {
            const Icon = item?.icon;
            const isActive = pathname === item?.href;
            return (
              <Link
                key={item?.href}
                href={item?.href ?? '/'}
                className={cn(
                  'flex items-center gap-2 rounded-lg px-4 py-2 text-sm font-medium transition-all',
                  isActive
                    ? 'bg-primary text-primary-foreground shadow-sm'
                    : 'text-muted-foreground hover:bg-secondary hover:text-secondary-foreground'
                )}
              >
                {Icon && <Icon className="h-4 w-4" />}
                <span className="hidden sm:inline">{item?.label}</span>
              </Link>
            );
          })}
        </nav>
      </div>
    </header>
  );
}
