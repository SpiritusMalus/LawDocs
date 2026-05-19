import Link from "next/link";
import { SITUATIONS, SituationId } from "@/lib/situations";
import { ArrowRight, ShoppingBag, Store, Landmark, Briefcase, Car, Building2, Plane, Lock, Gavel, AlertOctagon, Home, MapPin, GraduationCap, Droplets, Hammer, Wifi, HeartPulse, CalendarClock, HardHat, FileX, Wrench, PhoneOff, Dumbbell, HelpCircle } from "lucide-react";
import { ScrollReveal } from "@/components/ui/scroll-reveal";
import { type LucideIcon } from "lucide-react";


const SITUATION_ICONS: Record<SituationId, LucideIcon> = {
  shop: ShoppingBag,
  marketplace: Store,
  bank: Landmark,
  employer: Briefcase,
  insurance: Car,
  utility: Building2,
  airline: Plane,
  bank_block: Lock,
  court_order: Gavel,
  gibdd: AlertOctagon,
  rental_deposit: Home,
  tour_operator: MapPin,
  online_course: GraduationCap,
  neighbor_flood: Droplets,
  repair: Hammer,
  telecom: Wifi,
  medical: HeartPulse,
  ddu_delay: CalendarClock,
  ddu_defects: HardHat,
  ddu_termination: FileX,
  dtp_osago: Car,
  auto_repair: Wrench,
  debt_collector: PhoneOff,
  carsharing: Car,
  gym_refund: Dumbbell,
  other: HelpCircle,
};

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
          {SITUATIONS.map((s, i) => {
            const Icon = SITUATION_ICONS[s.id] ?? HelpCircle;
            return (
              <Link
                key={s.id}
                href={`/situations/${s.id}`}
                className={`group bg-white rounded-2xl border border-gray-100 p-6 shadow-sm hover:shadow-xl hover:bg-gray-900 hover:border-gray-900 transition-all duration-200 h-full flex flex-col${i === SITUATIONS.length - 1 && SITUATIONS.length % 3 === 1 ? " lg:col-span-2" : ""}`}
              >
                <div className="flex items-start gap-4 mb-3">
                  <div className="shrink-0 w-10 h-10 rounded-xl bg-primary/8 flex items-center justify-center group-hover:bg-white/10 transition-colors">
                    <Icon className="h-5 w-5 text-primary group-hover:text-blue-400 transition-colors" aria-hidden="true" />
                  </div>
                  <h3 className="text-base font-semibold text-gray-900 group-hover:text-white transition-colors leading-snug pt-1">
                    {s.title}
                  </h3>
                </div>
                <p className="text-sm text-gray-500 group-hover:text-gray-300 leading-relaxed mb-3 transition-colors">
                  {s.blurb}
                </p>
                <p className="text-xs text-gray-400 group-hover:text-gray-500 mb-4 transition-colors">
                  {s.examples}
                </p>
                <span className="mt-auto inline-flex items-center gap-1.5 text-sm font-medium text-primary group-hover:text-blue-400 transition-colors">
                  Оформить документ
                  <ArrowRight className="h-3.5 w-3.5 transition-transform group-hover:translate-x-0.5" aria-hidden="true" />
                </span>
              </Link>
            );
          })}
        </div>
      </div>
    </section>
  );
}
