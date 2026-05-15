import Link from "next/link";
import { CheckCircle, Clock, FileText, MessageCircle } from "lucide-react";
import { buttonVariants } from "@/components/ui/button";
import { YmGoal } from "@/components/analytics/ym-goal";

export const metadata = {
  title: "Заявка отправлена — LawDocs",
  description: "Мы получили вашу заявку и свяжемся в течение 2 часов в рабочее время.",
};

export default function ThanksPage() {
  return (
    <section className="bg-white py-24 px-4 min-h-[70vh] flex items-center">
      <YmGoal goal="lead_submitted" />
      <div className="max-w-xl mx-auto text-center">
        <div className="w-16 h-16 rounded-full bg-emerald-50 text-emerald-600 flex items-center justify-center mx-auto mb-6">
          <CheckCircle className="h-8 w-8" />
        </div>

        <h1 className="text-3xl md:text-4xl font-bold text-gray-900 mb-4">
          Заявка получена
        </h1>
        <p className="text-gray-500 mb-10 leading-relaxed">
          Спасибо! Мы изучаем вашу ситуацию и свяжемся в течение
          <span className="font-medium text-gray-700"> 2 часов</span> в рабочее время
          (Пн–Пт, 10:00–19:00 МСК).
        </p>

        <div className="bg-gray-50 rounded-2xl border border-gray-100 p-6 mb-10 text-left">
          <h2 className="font-semibold text-gray-900 mb-4">Что будет дальше</h2>
          <ol className="space-y-4">
            <li className="flex items-start gap-3">
              <Clock className="h-5 w-5 text-blue-500 mt-0.5 shrink-0" />
              <span className="text-sm text-gray-600">
                Свяжемся, уточним детали и подтвердим, что ситуация подходит под шаблон.
              </span>
            </li>
            <li className="flex items-start gap-3">
              <MessageCircle className="h-5 w-5 text-blue-500 mt-0.5 shrink-0" />
              <span className="text-sm text-gray-600">
                Пришлём счёт на 199 ₽ — оплата картой или СБП.
              </span>
            </li>
            <li className="flex items-start gap-3">
              <FileText className="h-5 w-5 text-blue-500 mt-0.5 shrink-0" />
              <span className="text-sm text-gray-600">
                После оплаты получите документ на email с инструкцией, куда его отнести.
              </span>
            </li>
          </ol>
        </div>

        <div className="flex flex-col sm:flex-row gap-3 justify-center mb-10">
          <Link href="/" className={buttonVariants({ variant: "outline" }) + " h-10 px-5"}>
            На главную
          </Link>
          <Link
            href="/situations"
            className={buttonVariants({ variant: "outline" }) + " h-10 px-5"}
          >
            Другие документы
          </Link>
        </div>

        <p className="text-xs text-gray-400 max-w-sm mx-auto leading-relaxed">
          Если документ понадобится другу или коллеге — расскажите о сервисе.
          Это лучшее, что можно сделать в знак благодарности.
        </p>
      </div>
    </section>
  );
}
