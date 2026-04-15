"use client";
import Link from "next/link";
import { usePathname } from "next/navigation";
import { cn } from "@/lib/utils";
import {
  LayoutDashboard, Table2, Grid2X2, FileText,
  Cpu, Settings, LogOut, Activity, ChevronRight,
} from "lucide-react";
import { useLogout } from "@/hooks/useAuth";
import { useAuthStore } from "@/store/auth";

const nav = [
  { href: "/dashboard", label: "Dashboard", icon: LayoutDashboard },
  { href: "/explorer", label: "Data Explorer", icon: Table2 },
  { href: "/pivot", label: "Pivot Table", icon: Grid2X2 },
  { href: "/reports", label: "Reports", icon: FileText },
  { href: "/products", label: "Products", icon: Cpu },
  { href: "/admin", label: "Admin", icon: Settings },
];

export function Sidebar() {
  const pathname = usePathname();
  const logout = useLogout();
  const { user } = useAuthStore();

  return (
    <aside className="flex flex-col w-60 bg-slate-900 text-white min-h-screen">
      {/* Brand */}
      <div className="flex items-center gap-2 px-5 py-5 border-b border-slate-700">
        <Activity className="h-6 w-6 text-blue-400" />
        <span className="font-bold text-lg tracking-tight">SoC Dashboard</span>
      </div>

      {/* Nav */}
      <nav className="flex-1 py-4 px-3 space-y-1">
        {nav.map(({ href, label, icon: Icon }) => {
          const active = pathname === href || pathname.startsWith(href + "/");
          return (
            <Link
              key={href}
              href={href}
              className={cn(
                "flex items-center gap-3 px-3 py-2.5 rounded-lg text-sm font-medium transition-colors",
                active
                  ? "bg-blue-600 text-white"
                  : "text-slate-300 hover:bg-slate-800 hover:text-white"
              )}
            >
              <Icon className="h-4 w-4 shrink-0" />
              {label}
              {active && <ChevronRight className="ml-auto h-4 w-4" />}
            </Link>
          );
        })}
      </nav>

      {/* User */}
      <div className="border-t border-slate-700 px-4 py-4">
        <div className="flex items-center gap-3 mb-3">
          <div className="h-8 w-8 rounded-full bg-blue-500 flex items-center justify-center text-sm font-bold">
            {user?.username?.[0]?.toUpperCase() ?? "?"}
          </div>
          <div className="min-w-0">
            <p className="text-sm font-medium truncate">{user?.username ?? "Guest"}</p>
            <p className="text-xs text-slate-400 capitalize">{user?.role ?? "viewer"}</p>
          </div>
        </div>
        <button
          onClick={logout}
          className="flex items-center gap-2 w-full px-3 py-2 rounded-lg text-sm text-slate-400 hover:bg-slate-800 hover:text-white transition-colors"
        >
          <LogOut className="h-4 w-4" />
          Sign out
        </button>
      </div>
    </aside>
  );
}
