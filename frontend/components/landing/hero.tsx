import Link from "next/link";
import { buttonVariants } from "@/components/ui/button";
import { FileText, ArrowRight, ShieldCheck, CheckCircle } from "lucide-react";
import { cn } from "@/lib/utils";

export function Hero() {
  return (
    <section className="relative overflow-hidden bg-gray-900 after:absolute after:bottom-0 after:left-0 after:right-0 after:h-16 after:bg-gradient-to-b after:from-transparent after:to-gray-50 after:pointer-events-none">
      {/* Subtle grid pattern */}
      <div
        className="absolute inset-0 opacity-[0.06]"
        style={{
          backgroundImage: "radial-gradient(circle, #60a5fa 1px, transparent 1px)",
          backgroundSize: "32px 32px",
        }}
      />
      {/* Glow */}
      <div className="absolute top-0 left-1/2 -translate-x-1/2 w-[800px] h-[500px] bg-blue-600/20 rounded-full blur-3xl" />
      <div className="absolute bottom-0 right-0 w-[400px] h-[300px] bg-indigo-600/10 rounded-full blur-3xl" />

      <div className="relative max-w-(--l-content) mx-auto px-4 py-20 md:py-24">
        <div className="flex flex-col lg:flex-row items-center gap-14 lg:gap-16">

          {/* Left column */}
          <div className="flex-1 text-center lg:text-left">
            <div className="animate-hero animate-hero-1 inline-flex items-center gap-2 bg-blue-500/10 border border-blue-400/20 text-blue-300 text-xs font-semibold px-3 py-1.5 rounded-full mb-6 tracking-wide uppercase">
              <ShieldCheck className="h-3.5 w-3.5" aria-hidden="true" />
              Шаблоны проверены юристом
            </div>

            <h1 className="animate-hero animate-hero-2 text-4xl sm:text-5xl md:text-6xl font-bold tracking-tight text-white mb-5 leading-[1.1]">
              Готовая <span className="text-blue-400">претензия</span>{" "}
              за <span className="text-blue-400">5&nbsp;минут</span>
              <br />— вместо 5&nbsp;000&nbsp;₽ у юриста
            </h1>

            <p className="animate-hero animate-hero-3 text-lg text-gray-400 mb-8 max-w-lg mx-auto lg:mx-0 leading-relaxed">
              Магазин не возвращает деньги, банк списал лишнее,
              маркетплейс кинул на возврат — опишите ситуацию,
              и получите документ со ссылками на статьи закона,
              расчётом неустойки и инструкцией куда отправить.
            </p>

            <div className="animate-hero animate-hero-4 flex flex-col sm:flex-row gap-3 justify-center lg:justify-start mb-4">
              <Link
                href="/situations"
                className={cn(
                  "inline-flex items-center justify-center h-12 px-6 text-base font-semibold rounded-lg",
                  "bg-blue-500 hover:bg-blue-400 text-white transition-colors"
                )}
              >
                <FileText className="h-5 w-5 mr-2" aria-hidden="true" />
                Получить документ
                <ArrowRight className="h-4 w-4 ml-2" aria-hidden="true" />
              </Link>
              <Link
                href="#how-it-works"
                className="inline-flex items-center justify-center h-12 px-6 text-base font-medium rounded-lg border border-gray-700 text-gray-300 hover:border-gray-500 hover:text-white transition-colors"
              >
                Как это работает
              </Link>
            </div>

            <p className="text-xs text-gray-500 mb-8">
              Вернём 199&nbsp;₽ в течение 7 дней, если документ не подойдёт
            </p>

            <div className="flex flex-wrap items-center justify-center lg:justify-start gap-x-6 gap-y-2 text-sm text-gray-400 mb-8">
              <span className="flex items-center gap-1.5"><span className="text-blue-400" aria-hidden="true">✓</span> Word + PDF</span>{" "}
              <span className="flex items-center gap-1.5"><span className="text-blue-400" aria-hidden="true">✓</span> Инструкция куда отправить</span>{" "}
              <span className="flex items-center gap-1.5"><span className="text-blue-400" aria-hidden="true">✓</span> Шаблоны проверены юристом</span>
            </div>

            <div className="flex flex-col items-center lg:items-start gap-2">
              <p className="text-xs text-gray-500">Оплата через ЮKassa — безопасно и быстро</p>
              <div className="flex items-center gap-3">
                <PaymentBadge label="Visa" />{" "}
                <PaymentBadge label="Мир" />{" "}
                <PaymentBadge label="Mastercard" />{" "}
                <PaymentBadge label="СБП" accent />
              </div>
            </div>
          </div>

          {/* Right column — document mockup */}
          <div className="hidden lg:block flex-shrink-0">
            <DocumentMockup />
          </div>

        </div>
      </div>
    </section>
  );
}

function DocumentMockup() {
  return (
    <div className="flex items-start gap-4">
      {/* Document */}
      <div className="relative">
        <div className="absolute -inset-4 bg-blue-500/10 rounded-3xl blur-2xl pointer-events-none" />
        <div className="relative bg-white rounded-2xl shadow-[0_2px_20px_rgba(0,0,0,0.14)] overflow-hidden border border-gray-200/60 w-[340px]">
          {/* Titlebar */}
          <div className="bg-gray-800 px-5 py-3 flex items-center gap-2">
            <div className="w-3 h-3 rounded-full bg-red-400/70" />
            <div className="w-3 h-3 rounded-full bg-yellow-400/70" />
            <div className="w-3 h-3 rounded-full bg-green-400/70" />
            <span className="ml-2 text-xs text-gray-400">претензия.docx</span>
          </div>
          {/* Document body */}
          <div className="p-6 font-mono text-xs leading-relaxed text-gray-700 space-y-3">
            <div className="text-right text-gray-500 text-[11px]">
              <div>Генеральному директору</div>
              <div>ООО «Wildberries»</div>
              <div className="mt-1">от Иванова Ивана Ивановича</div>
              <div>г. Москва</div>
            </div>
            <div className="text-center font-bold text-gray-900 text-sm py-2 tracking-wide">
              ПРЕТЕНЗИЯ № 2026-04-15
            </div>
            <div className="text-[11px] text-gray-600 leading-relaxed">
              15 апреля 2024 года я приобрёл товар артикул №<span className="text-blue-600">48291</span> стоимостью <span className="text-blue-600 font-semibold">3 490 ₽</span>...
            </div>
            <div className="text-[11px] text-gray-600 leading-relaxed">
              В соответствии со ст. 18 Закона РФ «О защите прав потребителей» от 07.02.1992 №<span className="text-blue-600">2300-1</span>...
            </div>
            <div className="border-t border-gray-100 pt-3 space-y-2">
              <div className="flex items-center gap-2 text-[11px] text-emerald-700 bg-emerald-50 rounded-lg px-3 py-2">
                <CheckCircle className="h-3.5 w-3.5 shrink-0" />
                Неустойка: <span className="font-semibold">1% за каждый день просрочки</span>
              </div>
              <div className="flex items-center gap-2 text-[11px] text-blue-700 bg-blue-50 rounded-lg px-3 py-2">
                <CheckCircle className="h-3.5 w-3.5 shrink-0" />
                Куда подать: Роспотребнадзор, суд
              </div>
            </div>
            <div className="pt-2 text-[11px] text-gray-400 flex items-center justify-between">
              <span>Подпись: _______________</span>
              <span>Дата: __.__.2024</span>
            </div>
          </div>
        </div>
        <div className="absolute -bottom-3 -right-3 bg-emerald-500 text-white text-xs font-bold px-3 py-1.5 rounded-full shadow-lg">
          Готов за 5 мин
        </div>
      </div>

      {/* Callouts */}
      <div className="flex flex-col gap-5 mt-[172px]">
        <CalloutLabel icon="🔗" text="Ссылка на статью закона" />
        <CalloutLabel icon="🧮" text="Расчёт неустойки автоматически" />
        <CalloutLabel icon="📮" text="Куда подать" />
      </div>
    </div>
  );
}

function CalloutLabel({ icon, text }: { icon: string; text: string }) {
  return (
    <div className="flex items-center gap-2">
      <div className="w-6 h-px bg-white/30 shrink-0" />
      <div className="flex items-center gap-1.5 bg-white/10 border border-white/20 rounded-lg px-2.5 py-1.5">
        <span className="text-sm leading-none">{icon}</span>
        <span className="text-[11px] text-gray-300 font-medium whitespace-nowrap">{text}</span>
      </div>
    </div>
  );
}

function PaymentBadge({ label, accent = false }: { label: string; accent?: boolean }) {
  return (
    <span
      className={`inline-flex items-center justify-center px-2.5 py-1 rounded-md text-xs font-semibold border ${
        accent
          ? "bg-green-500/10 border-green-500/30 text-green-400"
          : "bg-gray-800 border-gray-700 text-gray-400"
      }`}
    >
      {label}
    </span>
  );
}
