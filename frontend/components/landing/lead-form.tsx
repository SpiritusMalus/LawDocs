"use client";

import { useActionState, useEffect, useState } from "react";
import { useRouter, useSearchParams } from "next/navigation";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Textarea } from "@/components/ui/textarea";
import { SITUATIONS } from "@/lib/situations";
import { submitLead, type LeadState } from "@/lib/actions/submit-lead";
import { Loader2, AlertCircle } from "lucide-react";

const initialState: LeadState = { status: "idle" };

export function LeadForm() {
  const router = useRouter();
  const params = useSearchParams();
  const presetSituation = params.get("situation") ?? "";
  const [situation, setSituation] = useState(presetSituation);

  const [state, formAction, isPending] = useActionState(submitLead, initialState);

  useEffect(() => {
    if (state.status === "success") {
      router.push("/thanks");
    }
  }, [state.status, router]);

  return (
    <section id="lead-form" className="bg-white py-24 px-4 scroll-mt-16">
      <div className="max-w-2xl mx-auto">
        <div className="text-center mb-10">
          <h2 className="text-3xl font-bold text-gray-900 mb-3">
            Опишите ситуацию
          </h2>
          <p className="text-gray-500">
            Свяжемся в течение 2 часов в рабочее время и пришлём счёт на 500&nbsp;₽.
            После оплаты — готовый документ на email.
          </p>
        </div>

        <form
          action={formAction}
          className="bg-gray-50 rounded-2xl border border-gray-100 p-6 md:p-8 space-y-5"
        >
          <div className="space-y-2">
            <Label htmlFor="situation">Ситуация</Label>
            <select
              id="situation"
              name="situation"
              value={situation}
              onChange={(e) => setSituation(e.target.value)}
              className="flex h-9 w-full rounded-lg border border-border bg-background px-3 py-1 text-sm shadow-xs transition-colors focus-visible:border-ring focus-visible:outline-none focus-visible:ring-3 focus-visible:ring-ring/50"
            >
              <option value="">— выберите —</option>
              {SITUATIONS.map((s) => (
                <option key={s.id} value={s.id}>
                  {s.title}
                </option>
              ))}
              <option value="other">Другое / нет в списке</option>
            </select>
          </div>

          <div className="grid md:grid-cols-2 gap-5">
            <div className="space-y-2">
              <Label htmlFor="name">Как к вам обращаться</Label>
              <Input id="name" name="name" required placeholder="Иван" autoComplete="name" />
            </div>
            <div className="space-y-2">
              <Label htmlFor="contact">Телефон или email</Label>
              <Input
                id="contact"
                name="contact"
                required
                placeholder="+7 999 123-45-67 или ivan@mail.ru"
                autoComplete="email"
              />
            </div>
          </div>

          <div className="space-y-2">
            <Label htmlFor="description">Что произошло</Label>
            <Textarea
              id="description"
              name="description"
              required
              minLength={20}
              maxLength={2000}
              rows={5}
              placeholder="Купил пылесос 12 ноября, через неделю сломался. В магазине отказались возвращать деньги, ссылаясь на „технически сложный товар“…"
            />
            <p className="text-xs text-gray-400">
              Опишите своими словами: кто, когда, какая сумма, что вам отказали.
              Юридические термины не нужны.
            </p>
          </div>

          {/* Honeypot — invisible to users, visible to bots */}
          <div aria-hidden="true" className="absolute left-[-9999px] opacity-0 pointer-events-none">
            <label>
              Не заполняйте это поле
              <input type="text" name="website" tabIndex={-1} autoComplete="off" />
            </label>
          </div>

          <label className="flex items-start gap-2 text-xs text-gray-500 leading-relaxed cursor-pointer">
            <input
              type="checkbox"
              name="consent"
              required
              defaultChecked
              className="mt-0.5 h-4 w-4 rounded border-gray-300"
            />
            <span>
              Соглашаюсь с{" "}
              <a href="/legal/privacy" className="text-blue-600 underline-offset-4 hover:underline">
                политикой обработки персональных данных
              </a>{" "}
              и{" "}
              <a href="/legal/offer" className="text-blue-600 underline-offset-4 hover:underline">
                условиями оферты
              </a>
              . Понимаю, что для подготовки документа используется ИИ.
            </span>
          </label>

          {state.status === "error" && state.message && (
            <div className="flex items-start gap-2 text-sm text-destructive bg-destructive/5 border border-destructive/20 rounded-lg px-3 py-2">
              <AlertCircle className="h-4 w-4 mt-0.5 shrink-0" />
              <span>{state.message}</span>
            </div>
          )}

          <Button type="submit" size="lg" disabled={isPending} className="w-full h-11 text-base">
            {isPending ? (
              <>
                <Loader2 className="h-4 w-4 mr-2 animate-spin" />
                Отправляем…
              </>
            ) : (
              "Получить документ за 500 ₽"
            )}
          </Button>

          <p className="text-center text-xs text-gray-400">
            Отправляя заявку, вы ничего не платите. Счёт пришлём после согласования деталей.
          </p>
        </form>
      </div>
    </section>
  );
}
