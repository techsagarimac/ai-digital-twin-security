export function StatusDot({ on, label }: { on: boolean; label: string }) {
  return (
    <span className="inline-flex items-center gap-1.5 font-mono text-[11px] uppercase">
      <span className={`h-1.5 w-1.5 rounded-full ${on ? "bg-accent" : "bg-muted"}`} />
      {label}
    </span>
  );
}
