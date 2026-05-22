import Link from "next/link";
import {
  ArrowRight,
  ShoppingBag,
  Store,
  Landmark,
  Briefcase,
  Car,
  Shield,
  ShieldAlert,
  KeyRound,
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
import { type Situation, type SituationId } from "@/lib/situations";
import { getSituationPage } from "@/lib/situation-pages";
import { type LucideIcon } from "lucide-react";

const SITUATION_ICONS: Record<SituationId, LucideIcon> = {
  shop: ShoppingBag,
  marketplace: Store,
  bank: Landmark,
  employer: Briefcase,
  insurance: Shield,
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
  dtp_osago: ShieldAlert,
  auto_repair: Wrench,
  debt_collector: PhoneOff,
  carsharing: KeyRound,
  gym_refund: Dumbbell,
  other: HelpCircle,
};

interface SituationCardProps {
  situation: Situation;
  variant?: "dark" | "list";
  showLegal?: boolean;
  className?: string;
}

export function SituationCard({
  situation: s,
  variant = "list",
  showLegal = false,
  className = "",
}: SituationCardProps) {
  const Icon = SITUATION_ICONS[s.id] ?? HelpCircle;
  const page = showLegal ? getSituationPage(s.id) : null;
  const isDark = variant === "dark";

  return (
    <Link
      href={`/situations/${s.id}`}
      className={`group bg-white rounded-2xl border border-gray-100 p-6 shadow-sm flex flex-col transition-all ${
        isDark
          ? "duration-200 hover:shadow-xl hover:bg-gray-900 hover:border-gray-900 h-full"
          : "duration-150 hover:shadow-lg hover:bg-gray-50 hover:border-primary/20 hover:-translate-y-0.5"
      } ${className}`}
    >
      <div className="flex items-start gap-4 mb-3">
        <div
          className={`shrink-0 w-10 h-10 rounded-xl flex items-center justify-center transition-colors ${
            isDark
              ? "bg-primary/8 group-hover:bg-white/10"
              : "bg-primary/8 group-hover:bg-primary/10"
          }`}
        >
          <Icon
            className={`h-5 w-5 transition-colors ${
              isDark ? "text-primary group-hover:text-blue-400" : "text-primary"
            }`}
            aria-hidden="true"
          />
        </div>
        <h3
          className={`text-base font-semibold leading-snug pt-1 transition-colors ${
            isDark
              ? "text-gray-900 group-hover:text-white"
              : "text-gray-900 group-hover:text-primary"
          }`}
        >
          {s.title}
        </h3>
      </div>
      <p
        className={`text-sm leading-relaxed mb-4 flex-1 transition-colors ${
          isDark ? "text-gray-500 group-hover:text-gray-300" : "text-gray-600"
        }`}
      >
        {s.blurb}
      </p>
      {showLegal && page && (
        <p
          className={`text-xs leading-relaxed mb-4 truncate transition-colors ${
            isDark
              ? "text-gray-600 group-hover:text-gray-400"
              : "text-gray-600"
          }`}
        >
          {page.legalBasis
            .slice(0, 2)
            .map((l) => l.article)
            .join(" · ")}
        </p>
      )}
      <span
        className={`mt-auto inline-flex items-center gap-1.5 text-sm font-medium transition-colors ${
          isDark ? "text-primary group-hover:text-blue-400" : "text-primary"
        }`}
      >
        Подобрать документ
        <ArrowRight
          className="h-3.5 w-3.5 transition-transform group-hover:translate-x-0.5"
          aria-hidden="true"
        />
      </span>
    </Link>
  );
}
