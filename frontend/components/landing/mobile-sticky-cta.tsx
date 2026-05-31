"use client";

import { useEffect, useState } from "react";
import Link from "next/link";
import { FileText, ArrowRight } from "lucide-react";
import { DOCUMENT_PRICE_RUB } from "@/lib/pricing";

export function MobileStickyCTA() {
  const [visible, setVisible] = useState(false);

  useEffect(() => {
    const handleScroll = () => {
      setVisible(window.scrollY > 400);
    };
    window.addEventListener("scroll", handleScroll, { passive: true });
    return () => window.removeEventListener("scroll", handleScroll);
  }, []);

  return (
    <div
      className={`md:hidden fixed bottom-0 inset-x-0 z-50 transition-transform duration-300 ${
        visible ? "translate-y-0" : "translate-y-full"
      }`}
    >
      <div className="bg-white border-t border-gray-200 shadow-lg px-4 py-3 safe-area-bottom">
        <Link
          href="/situations"
          className="flex items-center justify-center gap-2 w-full h-12 rounded-xl bg-primary text-white text-sm font-semibold"
        >
          <FileText className="h-4 w-4" aria-hidden="true" />
          Получить документ — {DOCUMENT_PRICE_RUB}&nbsp;₽
          <ArrowRight className="h-4 w-4" aria-hidden="true" />
        </Link>
      </div>
    </div>
  );
}
