"use client";

import { useState } from "react";
import Link from "next/link";
import { Scale, Menu, X, LayoutDashboard } from "lucide-react";
import { buttonVariants } from "@/components/ui/button";
import { cn } from "@/lib/utils";

const NAV_LINKS = [
  { href: "/situations", label: "Ситуации" },
  { href: "/#how-it-works", label: "Как работает" },
];

export function Header({ isAuthenticated = false }: { isAuthenticated?: boolean }) {
  const [open, setOpen] = useState(false);

  return (
    <header className="border-b bg-white sticky top-0 z-50 backdrop-blur supports-[backdrop-filter]:bg-white/90">
      <div className="max-w-6xl mx-auto px-4 h-16 flex items-center justify-between">
        <Link
          href="/"
          className="flex items-center gap-2 font-semibold text-lg"
          onClick={() => setOpen(false)}
        >
          <Scale className="h-5 w-5 text-blue-600" aria-hidden="true" />
          <span>LawDocs</span>
        </Link>

        <nav className="hidden md:flex items-center gap-6 text-sm text-muted-foreground">
          {NAV_LINKS.map((link) => (
            <Link
              key={link.href}
              href={link.href}
              className="hover:text-foreground transition-colors py-2 px-1"
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
                "h-9 px-4 hidden md:inline-flex items-center gap-2 rounded-lg border border-gray-200 bg-gray-50 hover:bg-gray-100 text-sm font-medium text-gray-700 transition-colors"
              )}
            >
              <LayoutDashboard className="h-4 w-4" aria-hidden="true" />
              Мои заказы
            </Link>
          ) : (
            <>
              <Link
                href="/login"
                className="hidden md:inline-flex h-9 px-4 items-center text-sm font-medium text-gray-600 hover:text-gray-900 transition-colors"
              >
                Войти
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
            className="md:hidden inline-flex items-center justify-center h-9 w-9 rounded-lg text-gray-600 hover:bg-gray-100 transition-colors"
          >
            {open ? <X className="h-5 w-5" aria-hidden="true" /> : <Menu className="h-5 w-5" aria-hidden="true" />}
          </button>
        </div>
      </div>

      {open && (
        <div
          className="md:hidden fixed inset-0 bg-black/20 z-40"
          aria-hidden="true"
          onClick={() => setOpen(false)}
        />
      )}
      {open && (
        <div className="md:hidden border-t border-gray-100 bg-white relative z-50">
          <nav className="max-w-6xl mx-auto px-4 py-4 flex flex-col gap-1">
            {NAV_LINKS.map((link) => (
              <Link
                key={link.href}
                href={link.href}
                onClick={() => setOpen(false)}
                className="flex items-center min-h-11 px-3 py-2.5 text-sm text-gray-700 hover:bg-gray-50 rounded-lg transition-colors"
              >
                {link.label}
              </Link>
            ))}
            {isAuthenticated ? (
              <Link
                href="/dashboard"
                onClick={() => setOpen(false)}
                className="flex items-center gap-2 min-h-11 px-3 py-2.5 text-sm text-gray-700 hover:bg-gray-50 rounded-lg transition-colors mt-1"
              >
                <LayoutDashboard className="h-4 w-4" aria-hidden="true" />
                Мои заказы
              </Link>
            ) : (
              <>
                <Link
                  href="/login"
                  onClick={() => setOpen(false)}
                  className="flex items-center min-h-11 px-3 py-2.5 text-sm text-gray-700 hover:bg-gray-50 rounded-lg transition-colors mt-1"
                >
                  Войти
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
