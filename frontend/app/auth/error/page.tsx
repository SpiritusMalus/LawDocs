import type { Metadata } from "next";
import Link from "next/link";
import { buttonVariants } from "@/components/ui/button";
import { cn } from "@/lib/utils";

export const metadata: Metadata = {
  title: "Ошибка входа — LawDocs",
  robots: { index: false },
};

interface ErrorConfig {
  title: string;
  message: string;
  primaryHref: string;
  primaryLabel: string;
  secondaryHref?: string;
  secondaryLabel?: string;
}

const ERROR_CONFIG: Record<string, ErrorConfig> = {
  invalid_link: {
    title: "Ссылка устарела",
    message:
      "Магические ссылки действуют 15 минут. Эта уже истекла или была использована ранее.",
    primaryHref: "/",
    primaryLabel: "Оформить заново",
    secondaryHref: "mailto:lawdocsru@gmail.com",
    secondaryLabel: "Написать в поддержку",
  },
  missing_token: {
    title: "Ссылка повреждена",
    message:
      "В ссылке отсутствует токен — возможно, письмо было обрезано почтовым клиентом.",
    primaryHref: "/",
    primaryLabel: "Попробовать снова",
    secondaryHref: "mailto:lawdocsru@gmail.com",
    secondaryLabel: "Написать нам",
  },
  unavailable: {
    title: "Сервис недоступен",
    message: "Что-то пошло не так на нашей стороне. Попробуйте через пару минут.",
    primaryHref: "/",
    primaryLabel: "На главную",
    secondaryHref: "mailto:lawdocsru@gmail.com",
    secondaryLabel: "Сообщить об ошибке",
  },
  unauthorized: {
    title: "Нужно войти",
    message:
      "Для просмотра этой страницы необходимо войти. Оформите новый документ — мы пришлём ссылку для входа на email.",
    primaryHref: "/situations",
    primaryLabel: "Оформить документ",
    secondaryHref: "/",
    secondaryLabel: "На главную",
  },
};

const DEFAULT_CONFIG: ErrorConfig = ERROR_CONFIG["invalid_link"]!;

export default async function AuthErrorPage({
  searchParams,
}: {
  searchParams: Promise<{ reason?: string }>;
}) {
  const { reason } = await searchParams;
  const cfg = ERROR_CONFIG[reason ?? ""] ?? DEFAULT_CONFIG;

  return (
    <main className="bg-gray-50 py-24 px-4 min-h-[70vh] flex items-center">
      <div className="max-w-md mx-auto text-center bg-white rounded-2xl border border-gray-100 p-10">
        <div className="text-5xl mb-5">🔒</div>
        <h1 className="text-xl font-bold text-gray-900 mb-3">{cfg.title}</h1>
        <p className="text-gray-500 text-sm mb-8">{cfg.message}</p>

        <div className="flex flex-col sm:flex-row gap-3 justify-center">
          <Link href={cfg.primaryHref} className={cn(buttonVariants({}), "h-10 px-6")}>
            {cfg.primaryLabel}
          </Link>
          {cfg.secondaryHref && cfg.secondaryLabel && (
            <Link
              href={cfg.secondaryHref}
              className={cn(buttonVariants({ variant: "outline" }), "h-10 px-6")}
            >
              {cfg.secondaryLabel}
            </Link>
          )}
        </div>
      </div>
    </main>
  );
}
