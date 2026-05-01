import Link from "next/link";
import { Scale } from "lucide-react";
import { SITUATIONS } from "@/lib/situations";

export function Footer() {
  return (
    <footer className="border-t border-gray-100 bg-white">
      <div className="max-w-6xl mx-auto px-4 py-12">
        <div className="grid md:grid-cols-3 gap-10 mb-10">
          {/* Brand + disclaimer */}
          <div>
            <Link
              href="/"
              className="inline-flex items-center gap-2 font-semibold text-gray-900 mb-3"
            >
              <Scale className="h-5 w-5 text-blue-600" />
              <span>LawDocs</span>
            </Link>
            <p className="text-xs text-gray-400 leading-relaxed">
              Сервис не является юридической консультацией. Документы носят
              информационный характер. При формировании документа используются
              технологии искусственного интеллекта.
            </p>
          </div>

          {/* Situation links */}
          <div>
            <div className="text-xs font-semibold text-gray-400 uppercase tracking-wide mb-4">
              Ситуации
            </div>
            <ul className="space-y-2">
              {SITUATIONS.map((s) => (
                <li key={s.id}>
                  <Link
                    href={`/situations/${s.id}`}
                    className="text-sm text-gray-500 hover:text-gray-900 transition-colors"
                  >
                    {s.title}
                  </Link>
                </li>
              ))}
            </ul>
          </div>

          {/* Legal + contact */}
          <div>
            <div className="text-xs font-semibold text-gray-400 uppercase tracking-wide mb-4">
              Документы
            </div>
            <ul className="space-y-2">
              <li>
                <Link
                  href="/legal/offer"
                  className="text-sm text-gray-500 hover:text-gray-900 transition-colors"
                >
                  Договор-оферта
                </Link>
              </li>
              <li>
                <Link
                  href="/legal/privacy"
                  className="text-sm text-gray-500 hover:text-gray-900 transition-colors"
                >
                  Политика конфиденциальности
                </Link>
              </li>
              <li>
                <a
                  href="mailto:hi@lawdocs.ru"
                  className="text-sm text-gray-500 hover:text-gray-900 transition-colors"
                >
                  hi@lawdocs.ru
                </a>
              </li>
            </ul>
          </div>
        </div>

        <div className="border-t border-gray-100 pt-6 text-xs text-gray-400">
          © {new Date().getFullYear()} LawDocs. Для сложных случаев обратитесь к практикующему юристу.
        </div>
      </div>
    </footer>
  );
}
