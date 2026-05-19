"use client";

import { useState } from "react";
import Link from "next/link";
import {
  ArrowRight,
  Mail,
  ShoppingBag,
  Store,
  Landmark,
  Briefcase,
  Car,
  Building2,
  Plane,
  Lock,
  Gavel,
  AlertOctagon,
  Home,
  MapPin,
  GraduationCap,
  Droplets,
  Hammer,
  Wifi,
  HeartPulse,
  CalendarClock,
  HardHat,
  FileX,
  Wrench,
  PhoneOff,
  Dumbbell,
  HelpCircle,
} from "lucide-react";
import { SITUATIONS, type SituationId } from "@/lib/situations";
import { getSituationPage } from "@/lib/situation-pages";
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

type CategoryId =
  | "all"
  | "consumer"
  | "banking"
  | "labor"
  | "housing"
  | "transport"
  | "insurance"
  | "legal";

const CATEGORIES: { id: CategoryId; label: string }[] = [
  { id: "all", label: "Все" },
  { id: "consumer", label: "Потребитель" },
  { id: "housing", label: "Жильё" },
  { id: "transport", label: "Транспорт" },
  { id: "banking", label: "Банк" },
  { id: "insurance", label: "Страховая" },
  { id: "labor", label: "Работа" },
  { id: "legal", label: "Суд и долги" },
];

const SITUATION_CATEGORY: Record<SituationId, CategoryId> = {
  shop: "consumer",
  marketplace: "consumer",
  online_course: "consumer",
  gym_refund: "consumer",
  tour_operator: "consumer",
  medical: "consumer",
  telecom: "consumer",
  bank: "banking",
  bank_block: "banking",
  employer: "labor",
  utility: "housing",
  rental_deposit: "housing",
  neighbor_flood: "housing",
  repair: "housing",
  ddu_delay: "housing",
  ddu_defects: "housing",
  ddu_termination: "housing",
  airline: "transport",
  gibdd: "transport",
  auto_repair: "transport",
  carsharing: "transport",
  insurance: "insurance",
  dtp_osago: "insurance",
  court_order: "legal",
  debt_collector: "legal",
  other: "consumer",
};

export function SituationsGrid() {
  const [activeCategory, setActiveCategory] = useState<CategoryId>("all");

  const filtered = SITUATIONS.filter(
    (s) =>
      s.id !== "other" &&
      (activeCategory === "all" || SITUATION_CATEGORY[s.id] === activeCategory)
  );

  return (
    <section className="bg-gray-50 py-12 px-4">
      <div className="max-w-5xl mx-auto">
        {/* Chips */}
        <div className="flex flex-wrap gap-2 mb-8 items-center">
          {CATEGORIES.map((cat) => (
            <button
              key={cat.id}
              onClick={() => setActiveCategory(cat.id)}
              className={`px-4 py-1.5 rounded-full text-sm font-medium transition-colors duration-150 ${
                activeCategory === cat.id
                  ? "bg-gray-900 text-white"
                  : "bg-white border border-gray-200 text-gray-600 hover:border-gray-400 hover:text-gray-900"
              }`}
            >
              {cat.label}
            </button>
          ))}
          <a
            href="mailto:lawdocsru@gmail.com"
            className="flex items-center gap-1.5 px-4 py-1.5 rounded-full text-sm font-medium border border-dashed border-gray-300 text-gray-500 hover:border-gray-500 hover:text-gray-700 transition-colors duration-150 whitespace-nowrap"
          >
            <Mail className="h-3.5 w-3.5" />
            Не вижу свою ситуацию
          </a>
        </div>

        {/* Grid */}
        <div className="grid md:grid-cols-2 lg:grid-cols-3 gap-5">
          {filtered.map((s) => {
            const Icon = SITUATION_ICONS[s.id] ?? HelpCircle;
            const page = getSituationPage(s.id);
            return (
              <Link
                key={s.id}
                href={`/situations/${s.id}`}
                className="group bg-white rounded-2xl border border-gray-100 p-6 shadow-sm hover:shadow-lg hover:bg-gray-50 hover:border-primary/20 hover:-translate-y-0.5 transition-all duration-150 flex flex-col"
              >
                <div className="flex items-start gap-4 mb-3">
                  <div className="shrink-0 w-10 h-10 rounded-xl bg-primary/8 flex items-center justify-center group-hover:bg-primary/10 transition-colors">
                    <Icon className="h-5 w-5 text-primary" aria-hidden="true" />
                  </div>
                  <h2 className="font-semibold text-gray-900 group-hover:text-primary transition-colors leading-snug pt-1 text-base">
                    {s.title}
                  </h2>
                </div>
                <p className="text-sm text-gray-500 leading-relaxed mb-2 flex-1">{s.blurb}</p>
                <p className="text-xs text-gray-400 leading-relaxed mb-4">{s.examples}</p>
                {page && (
                  <p className="text-xs text-gray-300 leading-relaxed mb-4">
                    {page.legalBasis
                      .slice(0, 2)
                      .map((l) => l.article)
                      .join(" · ")}
                  </p>
                )}
                <span className="inline-flex items-center gap-1.5 text-sm font-medium text-primary">
                  Оформить документ
                  <ArrowRight className="h-3.5 w-3.5 transition-transform group-hover:translate-x-0.5" />
                </span>
              </Link>
            );
          })}
        </div>
      </div>
    </section>
  );
}
