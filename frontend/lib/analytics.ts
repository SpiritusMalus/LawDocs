// Яндекс.Метрика: отправка цели (goal). No-op, если счётчик не задан или
// код выполняется на сервере. Тип window.ym объявлен в global.d.ts.

export function ymGoal(goal: string, params?: Record<string, unknown>) {
  const id = Number(process.env.NEXT_PUBLIC_YM_COUNTER_ID);
  if (id && typeof window !== "undefined" && window.ym) {
    window.ym(id, "reachGoal", goal, params);
  }
}
