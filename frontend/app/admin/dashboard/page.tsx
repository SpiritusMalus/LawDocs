"use client";

import { useState, useEffect, useTransition, useCallback } from "react";
import { useRouter } from "next/navigation";
import { LogOut, ExternalLink } from "lucide-react";
import { Button } from "@/components/ui/button";
import { adminLogoutAction } from "../actions";

type Period = "day" | "week" | "month" | "all";

interface ProblemOrder {
  id: string;
  situation_id: string;
  status: string;
  amount: number;
  created_at: string;
}

interface Funnel {
  created: number;
  paid: number;
  completed: number;
}

interface Stats {
  period: Period;
  orders_total: number;
  orders_paid: number;
  revenue_kopecks: number;
  conversion_pct: number;
  funnel: Funnel;
  avg_create_to_pay_seconds: number | null;
  by_status: Record<string, number>;
  by_situation: { situation_id: string; count: number }[];
  problem_orders: ProblemOrder[];
}

const PERIOD_LABELS: Record<Period, string> = {
  day: "День",
  week: "Неделя",
  month: "Месяц",
  all: "Всё время",
};

const ymCounterId = process.env.NEXT_PUBLIC_YM_COUNTER_ID;
const ymUrl = ymCounterId
  ? `https://metrika.yandex.ru/dashboard?id=${ymCounterId}`
  : "https://metrika.yandex.ru/";

function formatRub(kopecks: number): string {
  return (kopecks / 100).toLocaleString("ru-RU", { maximumFractionDigits: 0 }) + " ₽";
}

function formatDuration(seconds: number | null): string {
  if (seconds === null) return "—";
  if (seconds < 60) return `${Math.round(seconds)} сек`;
  if (seconds < 3600) return `${Math.round(seconds / 60)} мин`;
  return `${(seconds / 3600).toFixed(1)} ч`;
}

export default function AdminDashboardPage() {
  const router = useRouter();
  const [period, setPeriod] = useState<Period>("week");
  const [stats, setStats] = useState<Stats | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [isPending, startTransition] = useTransition();

  const loadStats = useCallback(async (p: Period) => {
    setError(null);
    const res = await fetch(`/api/admin/stats?period=${p}`);
    if (res.status === 401) {
      router.push("/admin/login?next=/admin/dashboard");
      return;
    }
    if (!res.ok) {
      setError("Не удалось загрузить статистику");
      return;
    }
    const data = (await res.json()) as Stats;
    setStats(data);
  }, [router]);

  useEffect(() => {
    loadStats(period);
  }, [period, loadStats]);

  function handleLogout() {
    startTransition(async () => {
      await adminLogoutAction();
      router.push("/admin/login");
    });
  }

  return (
    <main className="min-h-screen bg-gray-50 py-10 px-4">
      <div className="max-w-4xl mx-auto">
        <div className="flex items-center justify-between mb-6">
          <h1 className="text-2xl font-bold text-gray-900">Дашборд</h1>
          <div className="flex items-center gap-3">
            <a
              href={ymUrl}
              target="_blank"
              rel="noopener noreferrer"
              className="flex items-center gap-1.5 text-sm font-medium text-gray-500 hover:text-gray-700 transition-colors"
            >
              <ExternalLink className="h-4 w-4" />
              Я.Метрика
            </a>
            <Button variant="ghost" size="sm" onClick={handleLogout} disabled={isPending}>
              <LogOut className="h-4 w-4 mr-2" />
              Выход
            </Button>
          </div>
        </div>

        {/* Переключатель периода */}
        <div className="flex gap-2 mb-6">
          {(Object.keys(PERIOD_LABELS) as Period[]).map((p) => (
            <button
              key={p}
              onClick={() => setPeriod(p)}
              className={`py-1.5 px-3 rounded-lg text-sm font-medium transition-colors ${
                period === p
                  ? "bg-primary text-primary-foreground"
                  : "bg-white border border-gray-200 text-gray-700 hover:bg-gray-100"
              }`}
            >
              {PERIOD_LABELS[p]}
            </button>
          ))}
        </div>

        {error && <p className="text-sm text-red-600 mb-4">{error}</p>}

        {stats && (
          <>
            {/* Карточки метрик */}
            <div className="grid grid-cols-2 md:grid-cols-4 gap-4 mb-8">
              <MetricCard label="Заказы" value={stats.orders_total.toString()} />
              <MetricCard label="Оплачено" value={stats.orders_paid.toString()} />
              <MetricCard label="Выручка" value={formatRub(stats.revenue_kopecks)} />
              <MetricCard label="Конверсия" value={`${stats.conversion_pct}%`} />
            </div>

            {/* Воронка по заказам */}
            <div className="bg-white rounded-2xl border border-gray-100 p-6 mb-8">
              <div className="flex items-baseline justify-between mb-4">
                <h2 className="font-semibold text-gray-900">Воронка по заказам</h2>
                <span className="text-sm text-gray-500">
                  Среднее время до оплаты:{" "}
                  <span className="font-medium text-gray-900">
                    {formatDuration(stats.avg_create_to_pay_seconds)}
                  </span>
                </span>
              </div>
              <FunnelView funnel={stats.funnel} />
            </div>

            <div className="grid md:grid-cols-2 gap-6 mb-8">
              {/* По статусам */}
              <div className="bg-white rounded-2xl border border-gray-100 p-6">
                <h2 className="font-semibold text-gray-900 mb-4">По статусам</h2>
                {Object.keys(stats.by_status).length === 0 ? (
                  <p className="text-sm text-gray-400">Нет данных за период</p>
                ) : (
                  <ul className="space-y-2">
                    {Object.entries(stats.by_status)
                      .sort((a, b) => b[1] - a[1])
                      .map(([status, count]) => (
                        <li key={status} className="flex justify-between text-sm">
                          <span className="text-gray-600">{status}</span>
                          <span className="font-medium text-gray-900">{count}</span>
                        </li>
                      ))}
                  </ul>
                )}
              </div>

              {/* Топ ситуаций */}
              <div className="bg-white rounded-2xl border border-gray-100 p-6">
                <h2 className="font-semibold text-gray-900 mb-4">Топ ситуаций</h2>
                {stats.by_situation.length === 0 ? (
                  <p className="text-sm text-gray-400">Нет данных за период</p>
                ) : (
                  <ul className="space-y-2">
                    {stats.by_situation.slice(0, 10).map((s) => (
                      <li key={s.situation_id} className="flex justify-between text-sm">
                        <span className="text-gray-600">{s.situation_id}</span>
                        <span className="font-medium text-gray-900">{s.count}</span>
                      </li>
                    ))}
                  </ul>
                )}
              </div>
            </div>

            {/* Проблемные заказы */}
            <div className="bg-white rounded-2xl border border-gray-100 p-6">
              <h2 className="font-semibold text-gray-900 mb-4">
                Проблемные заказы ({stats.problem_orders.length})
              </h2>
              {stats.problem_orders.length === 0 ? (
                <p className="text-sm text-gray-400">Сбоев за период нет 🎉</p>
              ) : (
                <div className="overflow-x-auto">
                  <table className="w-full text-sm">
                    <thead>
                      <tr className="text-left text-gray-400 border-b border-gray-100">
                        <th className="py-2 pr-4 font-medium">ID</th>
                        <th className="py-2 pr-4 font-medium">Ситуация</th>
                        <th className="py-2 pr-4 font-medium">Статус</th>
                        <th className="py-2 pr-4 font-medium">Сумма</th>
                        <th className="py-2 font-medium">Дата</th>
                      </tr>
                    </thead>
                    <tbody>
                      {stats.problem_orders.map((o) => (
                        <tr key={o.id} className="border-b border-gray-50">
                          <td className="py-2 pr-4 font-mono text-xs text-gray-500">
                            {o.id.slice(0, 8)}
                          </td>
                          <td className="py-2 pr-4 text-gray-700">{o.situation_id}</td>
                          <td className="py-2 pr-4">
                            <span
                              className={
                                o.status === "refunded" ? "text-amber-600" : "text-red-600"
                              }
                            >
                              {o.status}
                            </span>
                          </td>
                          <td className="py-2 pr-4 text-gray-700">{formatRub(o.amount)}</td>
                          <td className="py-2 text-gray-500">
                            {new Date(o.created_at).toLocaleDateString("ru-RU")}
                          </td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </div>
              )}
            </div>
          </>
        )}
      </div>
    </main>
  );
}

function FunnelView({ funnel }: { funnel: Funnel }) {
  if (funnel.created === 0) {
    return <p className="text-sm text-gray-400">Нет данных за период</p>;
  }

  const steps = [
    { label: "Создан", count: funnel.created },
    { label: "Оплачен", count: funnel.paid },
    { label: "Документ готов", count: funnel.completed },
  ];

  return (
    <div className="space-y-3">
      {steps.map((step) => {
        // % от первого шага (Создан). funnel.created > 0 здесь гарантирован.
        const pct = Math.round((step.count / funnel.created) * 100);
        return (
          <div key={step.label}>
            <div className="flex justify-between text-sm mb-1">
              <span className="text-gray-600">{step.label}</span>
              <span className="font-medium text-gray-900">
                {step.count} <span className="text-gray-400">({pct}%)</span>
              </span>
            </div>
            <div className="h-2.5 rounded-full bg-gray-100 overflow-hidden">
              <div
                className="h-full rounded-full bg-primary transition-all"
                style={{ width: `${pct}%` }}
              />
            </div>
          </div>
        );
      })}
    </div>
  );
}

function MetricCard({ label, value }: { label: string; value: string }) {
  return (
    <div className="bg-white rounded-2xl border border-gray-100 p-5">
      <p className="text-xs text-gray-400 uppercase tracking-wide font-medium">{label}</p>
      <p className="text-2xl font-bold text-gray-900 mt-1">{value}</p>
    </div>
  );
}
