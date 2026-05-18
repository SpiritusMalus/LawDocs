import Link from "next/link";
import { SITUATIONS } from "@/lib/situations";
import { ArrowRight } from "lucide-react";
import { ScrollReveal } from "@/components/ui/scroll-reveal";

export function Situations() {
  return (
    <section id="situations" className="bg-gray-50 border-y border-gray-100 py-24 px-4 scroll-mt-16">
      <div className="max-w-(--l-content) mx-auto">
        <ScrollReveal>
          <div className="mb-(--l-section-heading)">
            <h2 className="text-3xl font-bold text-gray-900 mb-3">
              С какими ситуациями работаем
            </h2>
            <p className="text-gray-500 max-w-xl">
              Типовые случаи, которые покрывают большинство обращений.
              Не нашли свою — напишите на lawdocsru@gmail.com.
            </p>
          </div>
        </ScrollReveal>

        <div className="grid md:grid-cols-2 lg:grid-cols-3 gap-4">
          {SITUATIONS.map((s, i) => (
            <ScrollReveal key={s.id} delay={i * 60} className={`h-full${i === SITUATIONS.length - 1 && SITUATIONS.length % 3 === 1 ? " lg:col-span-2" : ""}`}>
            <Link
              href={`/situations/${s.id}`}
              className="group bg-white rounded-2xl border border-gray-100 p-6 shadow-sm hover:shadow-md hover:border-primary/20 transition-all h-full flex flex-col"
            >
              <h3 className="text-lg font-semibold text-gray-900 mb-2 group-hover:text-primary transition-colors">
                {s.title}
              </h3>
              <p className="text-sm text-gray-500 leading-relaxed mb-4">
                {s.blurb}
              </p>
              <p className="text-xs text-gray-500 mb-4">
                {s.examples}
              </p>
              <span className="inline-flex items-center gap-1.5 text-sm font-medium text-primary">
                Оформить документ
                <ArrowRight className="h-3.5 w-3.5 transition-transform group-hover:translate-x-0.5" aria-hidden="true" />
              </span>
            </Link>
            </ScrollReveal>
          ))}
        </div>
      </div>
    </section>
  );
}
