import { cn } from "@/lib/utils";
import type { LucideIcon } from "lucide-react";

interface MetricCardProps {
  title: string;
  value: string | number;
  subtitle?: string;
  icon?: LucideIcon;
  trend?: "up" | "down" | "neutral";
  variant?: "default" | "success" | "warning" | "danger";
  className?: string;
}

const variantStyles = {
  default: "bg-white dark:bg-slate-800 border-slate-200",
  success: "bg-green-50 dark:bg-green-950 border-green-200",
  warning: "bg-amber-50 dark:bg-amber-950 border-amber-200",
  danger: "bg-red-50 dark:bg-red-950 border-red-200",
};

const valueStyles = {
  default: "text-slate-900 dark:text-white",
  success: "text-green-700 dark:text-green-400",
  warning: "text-amber-700 dark:text-amber-400",
  danger: "text-red-700 dark:text-red-400",
};

export function MetricCard({
  title,
  value,
  subtitle,
  icon: Icon,
  variant = "default",
  className,
}: MetricCardProps) {
  return (
    <div
      className={cn(
        "rounded-xl border p-5 shadow-sm",
        variantStyles[variant],
        className
      )}
    >
      <div className="flex items-start justify-between">
        <p className="text-xs font-semibold uppercase tracking-wider text-slate-500 dark:text-slate-400">
          {title}
        </p>
        {Icon && (
          <span className={cn("p-1.5 rounded-lg bg-white/60 dark:bg-slate-700/60", valueStyles[variant])}>
            <Icon className="h-4 w-4" />
          </span>
        )}
      </div>
      <p className={cn("mt-2 text-3xl font-extrabold", valueStyles[variant])}>{value}</p>
      {subtitle && (
        <p className="mt-1 text-xs text-slate-500 dark:text-slate-400">{subtitle}</p>
      )}
    </div>
  );
}
