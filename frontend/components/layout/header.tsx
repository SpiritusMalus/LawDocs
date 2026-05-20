"use client";

import { useState } from "react";
import Link from "next/link";
import { Scale, Menu, X, LayoutDashboard, FolderOpen } from "lucide-react";
import { buttonVariants } from "@/components/ui/button";
import { cn } from "@/lib/utils";

const NAV_LINKS = [
  { href: "/situations", label: "Ситуации" },
  { href: "/#how-it-works", label: "Как работает" },
];

export function Header({ isAuthenticated = false }: { isAuthenticated?: boolean }) {
  const [open, setOpen] = useState(false);

  return (
    <header className="bg-gray-900 sticky top-0 z-50 backdrop-blur supports-[backdrop-filter]:bg-gray-900/95">
      <div className="max-w-6xl mx-auto px-4 h-16 flex items-center justify-between">
        <Link
          href="/"
          className="flex items-center gap-2 font-semibold text-lg text-white"
          onClick={() => setOpen(false)}
        >
          <Scale className="h-5 w-5 text-blue-400" aria-hidden="true" />
          <span>LawDocs</span>
        </Link>

        <nav className="hidden md:flex items-center gap-6 text-sm text-gray-400">
          {NAV_LINKS.map((link) => (
            <Link
              key={link.href}
              href={link.href}
              className="hover:text-white transition-colors py-2 px-1"
            >
              {link.label}
            </Link>
          ))}
        </nav>

        <div className="flex items-center gap-2">
          {isAuthenticated ? (
            <Link
              href="/dashboard"
              className={cn(
                "h-9 px-4 hidden md:inline-flex items-center gap-2 rounded-lg border border-gray-700 bg-gray-800 hover:bg-gray-700 text-sm font-medium text-gray-300 transition-colors"
              )}
            >
              <LayoutDashboard className="h-4 w-4" aria-hidden="true" />
              Мои заказы
            </Link>
          ) : (
            <>
              <Link
                href="/login"
                className="hidden md:inline-flex h-9 px-4 items-center gap-2 text-sm font-medium text-gray-400 hover:text-white transition-colors"
              >
                <FolderOpen className="h-4 w-4" aria-hidden="true" />
                Мои документы
              </Link>
              <Link
                href="/situations"
                className={cn(buttonVariants({}), "h-9 px-4 hidden md:inline-flex")}
              >
                Получить за 199 ₽
              </Link>
            </>
          )}
          <button
            type="button"
            aria-label={open ? "Закрыть меню" : "Открыть меню"}
            aria-expanded={open}
            onClick={() => setOpen((v) => !v)}
            className="md:hidden inline-flex items-center justify-center h-9 w-9 rounded-lg text-gray-400 hover:bg-gray-800 transition-colors"
          >
            {open ? <X className="h-5 w-5" aria-hidden="true" /> : <Menu className="h-5 w-5" aria-hidden="true" />}
          </button>
        </div>
      </div>

      {open && (
        <div
          className="md:hidden fixed inset-0 bg-black/40 z-40"
          aria-hidden="true"
          onClick={() => setOpen(false)}
        />
      )}
      {open && (
        <div className="md:hidden border-t border-gray-800 bg-gray-900 relative z-50">
          <nav className="max-w-6xl mx-auto px-4 py-4 flex flex-col gap-1">
            {NAV_LINKS.map((link) => (
              <Link
                key={link.href}
                href={link.href}
                onClick={() => setOpen(false)}
                className="flex items-center min-h-11 px-3 py-2.5 text-sm text-gray-300 hover:bg-gray-800 rounded-lg transition-colors"
              >
                {link.label}
              </Link>
            ))}
            {isAuthenticated ? (
              <Link
                href="/dashboard"
                onClick={() => setOpen(false)}
                className="flex items-center gap-2 min-h-11 px-3 py-2.5 text-sm text-gray-300 hover:bg-gray-800 rounded-lg transition-colors mt-1"
              >
                <LayoutDashboard className="h-4 w-4" aria-hidden="true" />
                Мои заказы
              </Link>
            ) : (
              <>
                <Link
                  href="/login"
                  onClick={() => setOpen(false)}
                  className="flex items-center gap-2 min-h-11 px-3 py-2.5 text-sm text-gray-300 hover:bg-gray-800 rounded-lg transition-colors mt-1"
                >
                  <FolderOpen className="h-4 w-4" aria-hidden="true" />
                  Мои документы
                </Link>
                <Link
                  href="/situations"
                  onClick={() => setOpen(false)}
                  className={cn(buttonVariants({}), "h-11 mt-2")}
                >
                  Получить за 199 ₽
                </Link>
              </>
            )}
          </nav>
        </div>
      )}
    </header>
  );
}
