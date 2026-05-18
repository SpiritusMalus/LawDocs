import Link from "next/link";
import { Scale } from "lucide-react";

export function Footer() {
  return (
    <footer className="bg-gray-900">
      <div className="max-w-(--l-content-wide) mx-auto px-4 py-12">
        <div className="grid md:grid-cols-2 gap-10 mb-10">
          {/* Brand + disclaimer */}
          <div>
            <Link
              href="/"
              className="inline-flex items-center gap-2 font-semibold text-white mb-3"
            >
              <Scale className="h-5 w-5 text-blue-400" aria-hidden="true" />
              <span>LawDocs</span>
            </Link>
            <p className="text-xs text-gray-500 leading-relaxed">
              Сервис не является юридической консультацией. Документы носят
              информационный характер. При формировании документа используются
              технологии искусственного интеллекта.
            </p>
          </div>

          {/* Legal + contact */}
          <div>
            <div className="text-xs font-semibold text-gray-500 uppercase tracking-wide mb-4">
              Ссылки
            </div>
            <ul className="space-y-0.5">
              <li>
                <Link
                  href="/about"
                  className="flex items-center min-h-11 text-sm text-gray-400 hover:text-white transition-colors"
                >
                  О сервисе
                </Link>
              </li>
              <li>
                <Link
                  href="/legal/offer"
                  className="flex items-center min-h-11 text-sm text-gray-400 hover:text-white transition-colors"
                >
                  Договор-оферта
                </Link>
              </li>
              <li>
                <Link
                  href="/legal/privacy"
                  className="flex items-center min-h-11 text-sm text-gray-400 hover:text-white transition-colors"
                >
                  Политика конфиденциальности
                </Link>
              </li>
              <li>
                <a
                  href="mailto:lawdocsru@gmail.com"
                  className="flex items-center min-h-11 text-sm text-gray-400 hover:text-white transition-colors"
                >
                  lawdocsru@gmail.com
                </a>
              </li>
            </ul>
          </div>
        </div>

        <div className="border-t border-gray-800 pt-6 text-xs text-gray-600">
          © {new Date().getFullYear()} LawDocs
        </div>
      </div>
    </footer>
  );
}
