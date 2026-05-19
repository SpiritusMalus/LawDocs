import { SITUATIONS } from "@/lib/situations";
import { ScrollReveal } from "@/components/ui/scroll-reveal";
import { SituationCard } from "@/components/situation-card";

export function Situations() {
  return (
    <section id="situations" className="bg-gray-50 border-y border-gray-100 py-24 px-4 scroll-mt-16">
      <div className="max-w-(--l-content) mx-auto">
        <ScrollReveal>
          <div className="mb-(--l-section-heading)">
            <h2 className="text-4xl font-bold text-gray-900 mb-3 tracking-tight">
              С чем приходят чаще всего
            </h2>
            <p className="text-gray-500 max-w-xl text-lg">
              Типовые случаи, которые покрывают большинство обращений.
              Не нашли свою — напишите на lawdocsru@gmail.com.
            </p>
          </div>
        </ScrollReveal>

        <div className="grid md:grid-cols-2 lg:grid-cols-3 gap-4">
          {SITUATIONS.map((s, i) => (
            <SituationCard
              key={s.id}
              situation={s}
              variant="dark"
              className={
                i === SITUATIONS.length - 1 && SITUATIONS.length % 3 === 1
                  ? "lg:col-span-2"
                  : ""
              }
            />
          ))}
        </div>
      </div>
    </section>
  );
}
