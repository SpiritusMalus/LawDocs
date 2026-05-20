import Link from "next/link";
import { SITUATIONS } from "@/lib/situations";
import { ScrollReveal } from "@/components/ui/scroll-reveal";
import { SituationCard } from "@/components/situation-card";
import { ArrowRight } from "lucide-react";

export function Situations() {
  const featured = SITUATIONS.filter((s) => s.featured);

  return (
    <section id="situations" className="bg-gray-50 border-y border-gray-100 py-24 px-4 scroll-mt-16">
      <div className="max-w-(--l-content) mx-auto">
        <ScrollReveal>
          <div className="mb-(--l-section-heading)">
            <h2 className="text-4xl font-bold text-gray-900 mb-3 tracking-tight">
              С чем чаще всего приходят
            </h2>
            <p className="text-gray-500 max-w-xl text-lg">
              Три самые частые ситуации. Полный список — на странице ситуаций.
            </p>
          </div>
        </ScrollReveal>

        <div className="grid md:grid-cols-2 lg:grid-cols-3 gap-4 mb-8">
          {featured.map((s) => (
            <SituationCard key={s.id} situation={s} variant="dark" />
          ))}
        </div>

        <div className="flex justify-center">
          <Link
            href="/situations"
            className="inline-flex items-center gap-2 px-6 py-3 text-base font-medium text-gray-900 hover:text-blue-600 transition-colors"
          >
            Все ситуации (25)
            <ArrowRight className="h-4 w-4" />
          </Link>
        </div>
      </div>
    </section>
  );
}
