import { ReactNode } from "react";

interface ResponsiveTableProps {
  children: ReactNode;
  className?: string;
}

export function ResponsiveTable({ children, className = "" }: ResponsiveTableProps) {
  return (
    <div className={`overflow-x-auto -mx-4 sm:mx-0 ${className}`}>
      <div className="inline-block min-w-full align-middle">
        <div className="overflow-hidden border-b border-border sm:rounded-lg">
          {children}
        </div>
      </div>
    </div>
  );
}

export function ResponsiveTableWrapper({ children }: { children: ReactNode }) {
  return (
    <div className="overflow-x-auto">
      <div className="inline-block min-w-full align-middle">
        {children}
      </div>
    </div>
  );
}
