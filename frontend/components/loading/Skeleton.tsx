import { cn } from "@/lib/utils";

interface SkeletonProps {
  className?: string;
}

export function Skeleton({ className }: SkeletonProps) {
  return (
    <div
      className={cn(
        "animate-pulse rounded-md bg-muted",
        className
      )}
    />
  );
}

export function TableSkeleton({ rows = 5 }: { rows?: number }) {
  return (
    <div className="space-y-3">
      {Array.from({ length: rows }).map((_, i) => (
        <div key={i} className="flex gap-4">
          <Skeleton className="h-12 flex-1" />
          <Skeleton className="h-12 w-20" />
          <Skeleton className="h-12 w-24" />
          <Skeleton className="h-12 w-20" />
        </div>
      ))}
    </div>
  );
}

export function CardSkeleton() {
  return (
    <div className="rounded-lg border bg-card p-6 space-y-3">
      <Skeleton className="h-4 w-24" />
      <Skeleton className="h-8 w-32" />
    </div>
  );
}

export function ChartSkeleton() {
  return (
    <div className="w-full h-[400px] rounded-lg border bg-card p-4">
      <div className="flex flex-col h-full justify-end space-y-2">
        {Array.from({ length: 8 }).map((_, i) => {
          const height = `${Math.random() * 60 + 20}%`;
          return (
            <div
              key={i}
              className="w-full animate-pulse rounded-md bg-muted"
              style={{ height }}
            />
          );
        })}
      </div>
    </div>
  );
}
