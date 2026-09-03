import { FileText } from 'lucide-react';

export function Footer() {
  return (
    <footer className="w-full border-t bg-foreground/[0.03]">
      <div className="mx-auto flex h-12 max-w-[1200px] items-center justify-between px-4 text-xs text-muted-foreground">
        <div className="flex items-center gap-2">
          <FileText className="h-3.5 w-3.5" />
          <span className="font-mono">SCK CEN</span>
        </div>
        <span className="font-mono">QPS Slide Reviewer</span>
        <span className="font-mono">ISC: Restricted</span>
      </div>
    </footer>
  );
}
