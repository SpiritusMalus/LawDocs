import Link from "next/link";
import { buttonVariants } from "@/components/ui/button";
import { FileText, ArrowRight, ShieldCheck } from "lucide-react";

export function Hero() {
  return (
    <section className="relative overflow-hidden bg-white">
      <div
        className="absolute inset-0 opacity-[0.04]"
        style={{
          backgroundImage: "radial-gradient(circle, #1d4ed8 1.5px, transparent 1.5px)",
          backgroundSize: "28px 28px",
        }}
      />
      <div className="absolute -top-32 left-1/2 -translate-x-1/2 w-[600px] h-[400px] bg-blue-500/10 rounded-full blur-3xl" />

      <div className="relative max-w-5xl mx-auto px-4 py-24 md:py-28 text-center">
        <div className="animate-hero animate-hero-1 inline-flex items-center gap-2 bg-blue-50 border border-blue-100 text-blue-700 text-xs font-semibold px-3 py-1.5 rounded-full mb-8 tracking-wide uppercase">
          <ShieldCheck className="h-3.5 w-3.5" />
          Шаблоны проверены практикующим юристом
        </div>

        <h1 className="animate-hero animate-hero-2 text-4xl sm:text-5xl md:text-6xl font-bold tracking-tight text-gray-900 mb-6 leading-[1.1]">
          Готовый юридический документ{" "}
          <span className="text-blue-600">за 5 минут</span>
          <br />— 199&nbsp;₽
        </h1>

        <p className="animate-hero animate-hero-3 text-lg md:text-xl text-gray-500 mb-10 max-w-2xl mx-auto leading-relaxed">
          Опишите проблему — получите претензию или жалобу,
          оформленную по всем правилам. С формулой расчёта неустойки,
          ссылками на статьи закона и инструкцией «куда нести».
        </p>

        <div className="animate-hero animate-hero-4 flex flex-col sm:flex-row gap-3 justify-center mb-5">
          <Link
            href="/situations"
            className={buttonVariants({ size: "lg" }) + " h-12 px-6 text-base"}
          >
            <FileText className="h-5 w-5 mr-2" />
            Получить документ
            <ArrowRight className="h-4 w-4 ml-2" />
          </Link>
          <Link
            href="#how-it-works"
            className={buttonVariants({ size: "lg", variant: "outline" }) + " h-12 px-6 text-base"}
          >
            Как это работает
          </Link>
        </div>

        <p className="text-xs text-gray-400 mb-10">
          Если документ не подойдёт — вернём деньги без вопросов
        </p>

        <div className="flex flex-wrap items-center justify-center gap-x-8 gap-y-3 text-sm text-gray-500 mb-10">
          <span className="flex items-center gap-1.5"><span className="text-blue-500">✓</span> Word + PDF</span>
          <span className="flex items-center gap-1.5"><span className="text-blue-500">✓</span> Инструкция куда отправить</span>
          <span className="flex items-center gap-1.5"><span className="text-blue-500">✓</span> Шаблоны проверены юристом</span>
        </div>

        <div className="flex flex-col items-center gap-2">
          <p className="text-xs text-gray-400">Оплата через ЮKassa — безопасно и быстро</p>
          <div className="flex items-center gap-3">
            <PaymentBadge label="Visa" />
            <PaymentBadge label="Мир" />
            <PaymentBadge label="Mastercard" />
            <PaymentBadge label="СБП" accent />
          </div>
        </div>
      </div>
    </section>
  );
}

function PaymentBadge({ label, accent = false }: { label: string; accent?: boolean }) {
  return (
    <span
      className={`inline-flex items-center justify-center px-2.5 py-1 rounded-md text-xs font-semibold border ${
        accent
          ? "bg-green-50 border-green-200 text-green-700"
          : "bg-gray-50 border-gray-200 text-gray-500"
      }`}
    >
      {label}
    </span>
  );
}
