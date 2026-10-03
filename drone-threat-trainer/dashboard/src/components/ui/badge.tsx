import * as React from "react";

export interface BadgeProps extends React.HTMLAttributes<HTMLDivElement> {
  variant?: "default" | "secondary" | "destructive" | "outline" | "cyan" | "amber" | "green";
}

export function Badge({ className = "", variant = "default", children, ...props }: BadgeProps) {
  let variantStyles = "bg-primary text-primary-foreground";
  if (variant === "secondary") variantStyles = "bg-slate-800 text-slate-300";
  if (variant === "destructive") variantStyles = "bg-red-500/20 text-red-400 border border-red-500/40";
  if (variant === "cyan") variantStyles = "bg-cyan-500/10 text-cyan-400 border border-cyan-500/30";
  if (variant === "amber") variantStyles = "bg-amber-500/10 text-amber-400 border border-amber-500/30";
  if (variant === "green") variantStyles = "bg-emerald-500/10 text-emerald-400 border border-emerald-500/30";

  return (
    <div
      className={`inline-flex items-center rounded-full px-2.5 py-0.5 text-xs font-semibold tracking-wider uppercase transition-colors ${variantStyles} ${className}`}
      {...props}
    >
      {children}
    </div>
  );
}

export interface ProgressProps extends React.HTMLAttributes<HTMLDivElement> {
  value?: number;
  indicatorColor?: string;
}

export function Progress({ className = "", value = 0, indicatorColor = "bg-cyan-500", ...props }: ProgressProps) {
  const clampedValue = Math.min(100, Math.max(0, value));
  return (
    <div className={`relative h-2 w-full overflow-hidden rounded-full bg-slate-800 ${className}`} {...props}>
      <div
        className={`h-full transition-all duration-500 ease-out ${indicatorColor}`}
        style={{ width: `${clampedValue}%` }}
      />
    </div>
  );
}
