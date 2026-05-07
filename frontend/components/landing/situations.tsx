import Link from "next/link";
import { SITUATIONS } from "@/lib/situations";
import { ArrowRight } from "lucide-react";

export function Situations() {
  return (
    <section id="situations" className="bg-gray-50 border-y border-gray-100 py-24 px-4 scroll-mt-16">
      <div className="max-w-5xl mx-auto">
        <div className="text-center mb-14">
          <h2 className="text-3xl font-bold text-gray-900 mb-3">
            С какими ситуациями работаем
          </h2>
          <p className="text-gray-500 max-w-xl mx-auto">
            Семь типовых случаев, которые покрывают большинство обращений.
            Не нашли свою — напишите на hi@lawdocs.ru.
          </p>
        </div>

        <div className="grid md:grid-cols-2 lg:grid-cols-3 gap-4">
          {SITUATIONS.map((s) => (
            <Link
              key={s.id}
              href={`/situations/${s.id}`}
              className="group bg-white rounded-2xl border border-gray-100 p-6 shadow-sm hover:shadow-md hover:border-blue-200 transition-all"
            >
              <h3 className="font-semibold text-gray-900 mb-2 group-hover:text-blue-600 transition-colors">
                {s.title}
              </h3>
              <p className="text-sm text-gray-500 leading-relaxed mb-4">
                {s.blurb}
              </p>
              <p className="text-xs text-gray-400 mb-4">
                {s.examples}
              </p>
              <span className="inline-flex items-center gap-1.5 text-sm font-medium text-blue-600">
                Оформить документ
                <ArrowRight className="h-3.5 w-3.5 transition-transform group-hover:translate-x-0.5" />
              </span>
            </Link>
          ))}
        </div>
      </div>
    </section>
  );
}
