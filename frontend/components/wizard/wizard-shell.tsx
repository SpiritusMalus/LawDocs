"use client";

import { useState, useTransition, useEffect, useMemo } from "react";
import { useRouter } from "next/navigation";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Textarea } from "@/components/ui/textarea";
import { ChevronLeft, ChevronRight, Loader2, AlertCircle, ServerCrash } from "lucide-react";
import type { WizardStep, WizardField } from "@/lib/wizard-types";
import { submitWizard } from "@/lib/actions/submit-wizard";
import { ymGoal } from "@/lib/analytics";

const LS_EMAIL_KEY = "lawdocs_email";
// Подполя адреса: каждое необязательно по отдельности, но хотя бы одно должно
// быть заполнено (зеркало серверной validate_address).
const ADDRESS_SUBFIELD_IDS = [
  "address_city",
  "address_street",
  "address_house",
  "address_building",
  "address_structure",
  "address_apartment",
];
const CONTACT_FIELDS = ["full_name", "phone", ...ADDRESS_SUBFIELD_IDS, "email"] as const;

function stepHasAddress(fields: WizardField[]): boolean {
  return fields.some((f) => ADDRESS_SUBFIELD_IDS.includes(f.id));
}
function isAddressEmpty(answers: Record<string, string>): boolean {
  return ADDRESS_SUBFIELD_IDS.every((id) => !answers[id]?.trim());
}
const ADDRESS_REQUIRED_MSG = "Укажите адрес проживания — хотя бы город или населённый пункт.";

// Адрес/сайт магазина (shop): каждое поле необязательно, но хотя бы одно должно
// быть заполнено (зеркало серверной validate_store_address).
const STORE_ADDRESS_FIELD_IDS = [
  "store_address_city",
  "store_address_street",
  "store_address_house",
  "store_address_building",
  "store_address_structure",
  "store_site",
];
function stepHasStoreAddress(fields: WizardField[]): boolean {
  return fields.some((f) => STORE_ADDRESS_FIELD_IDS.includes(f.id));
}
function isStoreAddressEmpty(answers: Record<string, string>): boolean {
  return STORE_ADDRESS_FIELD_IDS.every((id) => !answers[id]?.trim());
}
const STORE_ADDRESS_REQUIRED_MSG = "Укажите адрес магазина или его сайт — хотя бы одно поле.";

// «дд.мм.гггг» → Date с проверкой реального календарного дня (31.02 → null).
function parseRuDate(value: string): Date | null {
  const m = value.match(/^(\d{2})\.(\d{2})\.(\d{4})$/);
  if (!m) return null;
  const day = +m[1]!, month = +m[2]!, year = +m[3]!;
  const d = new Date(year, month - 1, day);
  if (d.getFullYear() !== year || d.getMonth() !== month - 1 || d.getDate() !== day) return null;
  return d;
}

// Проверка дат: формат, not_future, и cross-field (min_field/max_field).
// Зеркало серверной validate_dates — мгновенная обратная связь до отправки.
function getDateErrors(
  fields: WizardField[],
  answers: Record<string, string>,
  fieldById: Map<string, WizardField>,
): string[] {
  const errors: string[] = [];
  const today = new Date();
  today.setHours(0, 0, 0, 0);

  for (const f of fields) {
    if (f.type !== "date") continue;
    const raw = answers[f.id]?.trim();
    if (!raw) continue;

    const d = parseRuDate(raw);
    if (!d) {
      errors.push(`«${f.label}»: неверная дата. Формат — дд.мм.гггг.`);
      continue;
    }
    if (f.not_future && d > today) {
      errors.push(`«${f.label}»: дата не может быть в будущем.`);
    }
    if (f.min_field) {
      const other = answers[f.min_field]?.trim();
      const od = other ? parseRuDate(other) : null;
      if (od && d < od) {
        const label = fieldById.get(f.min_field)?.label ?? f.min_field;
        errors.push(`«${f.label}» не может быть раньше, чем «${label}» (${other}).`);
      }
    }
    if (f.max_field) {
      const other = answers[f.max_field]?.trim();
      const od = other ? parseRuDate(other) : null;
      if (od && d > od) {
        const label = fieldById.get(f.max_field)?.label ?? f.max_field;
        errors.push(`«${f.label}» не может быть позже, чем «${label}» (${other}).`);
      }
    }
  }
  return errors;
}

interface WizardShellProps {
  steps: WizardStep[];
  situationId: string;
  hasBackend?: boolean;
  isAuthenticated?: boolean;
  error?: boolean;
}

export function WizardShell({ steps, situationId, hasBackend = false, isAuthenticated = false, error = false }: WizardShellProps) {
  const router = useRouter();
  const [currentStep, setCurrentStep] = useState(0);
  const [answers, setAnswers] = useState<Record<string, string>>({});
  const [fieldErrors, setFieldErrors] = useState<string[]>([]);
  // id невалидных полей текущего шага — для красной подсветки самих полей.
  const [invalidFieldIds, setInvalidFieldIds] = useState<string[]>([]);
  const [dateErrors, setDateErrors] = useState<string[]>([]);
  const [submitError, setSubmitError] = useState<string | null>(null);
  // Согласие (оферта + ПДн) — обязательная галочка на финальном шаге.
  const [consentAccepted, setConsentAccepted] = useState(false);
  const [consentError, setConsentError] = useState(false);

  // Плоская карта всех полей всех шагов — для cross-field валидации дат
  // (поле может ссылаться на дату с предыдущего шага) и подстановки меток.
  const fieldById = useMemo(() => {
    const map = new Map<string, WizardField>();
    for (const s of steps) for (const f of s.fields) map.set(f.id, f);
    return map;
  }, [steps]);
  const [emailSent, setEmailSent] = useState(false);
  const [isPending, startTransition] = useTransition();

  useEffect(() => {
    ymGoal("wizard_started", { situation: situationId });
  }, [situationId]);

  // Pre-fill contact fields from last order (if authenticated) + localStorage email
  useEffect(() => {
    async function prefill() {
      if (isAuthenticated) {
        try {
          const res = await fetch("/api/user/contact", { cache: "no-store" });
          if (res.ok) {
            const data: Record<string, string> = await res.json();
            setAnswers((prev) => {
              const updates: Record<string, string> = {};
              for (const key of CONTACT_FIELDS) {
                if (data[key] && !prev[key]) updates[key] = data[key];
              }
              return Object.keys(updates).length ? { ...prev, ...updates } : prev;
            });
            return;
          }
        } catch {}
      }
      // Fallback: pre-fill email from localStorage
      try {
        const saved = localStorage.getItem(LS_EMAIL_KEY);
        if (saved) setAnswers((prev) => ({ ...prev, email: prev["email"] ?? saved }));
      } catch {}
    }
    prefill();
  }, [isAuthenticated]);

  const step = steps[currentStep]!;
  const isFirst = currentStep === 0;
  const isLast = currentStep === steps.length - 1;
  const progressPct = Math.round(((currentStep + 1) / steps.length) * 100);

  function getMissingRequiredFields(fields: WizardField[]): WizardField[] {
    return fields.filter((f) => f.required && !answers[f.id]?.trim());
  }

  function handleNext() {
    const missingFields = getMissingRequiredFields(step.fields);
    if (missingFields.length > 0) {
      setFieldErrors(missingFields.map((f) => f.label));
      setInvalidFieldIds(missingFields.map((f) => f.id));
      return;
    }
    const addr = stepHasAddress(step.fields) && isAddressEmpty(answers) ? [ADDRESS_REQUIRED_MSG] : [];
    const storeAddr =
      stepHasStoreAddress(step.fields) && isStoreAddressEmpty(answers) ? [STORE_ADDRESS_REQUIRED_MSG] : [];
    const problems = [...addr, ...storeAddr, ...getDateErrors(step.fields, answers, fieldById)];
    if (problems.length > 0) {
      setFieldErrors([]);
      setDateErrors(problems);
      return;
    }
    setFieldErrors([]);
    setDateErrors([]);
    ymGoal("wizard_step_completed", { step: currentStep + 1, situation: situationId });
    setCurrentStep((s) => s + 1);
    window.scrollTo({ top: 0, behavior: "smooth" });
  }

  function handleBack() {
    setFieldErrors([]);
    setInvalidFieldIds([]);
    setDateErrors([]);
    setSubmitError(null);
    setCurrentStep((s) => s - 1);
    window.scrollTo({ top: 0, behavior: "smooth" });
  }

  function handleChange(fieldId: string, value: string) {
    setAnswers((prev) => ({ ...prev, [fieldId]: value }));
    if (fieldErrors.length > 0) setFieldErrors([]);
    if (dateErrors.length > 0) setDateErrors([]);
    setInvalidFieldIds((prev) => (prev.includes(fieldId) ? prev.filter((id) => id !== fieldId) : prev));
  }

  function handleSubmit() {
    const missingFields = getMissingRequiredFields(step.fields);
    if (missingFields.length > 0) {
      setFieldErrors(missingFields.map((f) => f.label));
      setInvalidFieldIds(missingFields.map((f) => f.id));
      return;
    }
    // На отправке проверяем даты всей формы (cross-field может тянуться через шаги).
    const allFields = steps.flatMap((s) => s.fields);
    const addr = stepHasAddress(allFields) && isAddressEmpty(answers) ? [ADDRESS_REQUIRED_MSG] : [];
    const storeAddr =
      stepHasStoreAddress(allFields) && isStoreAddressEmpty(answers) ? [STORE_ADDRESS_REQUIRED_MSG] : [];
    const problems = [...addr, ...storeAddr, ...getDateErrors(allFields, answers, fieldById)];
    if (problems.length > 0) {
      setFieldErrors([]);
      setDateErrors(problems);
      return;
    }
    if (!consentAccepted) {
      setDateErrors([]);
      setConsentError(true);
      return;
    }
    setDateErrors([]);
    setConsentError(false);
    setSubmitError(null);
    ymGoal("wizard_submitted", { situation: situationId });
    startTransition(async () => {
      const result = await submitWizard({ situationId, answers, offerAccepted: consentAccepted });
      if (result.status === "redirect" && result.orderId) {
        try { localStorage.setItem(LS_EMAIL_KEY, answers["email"] ?? ""); } catch {}
        router.push(`/orders/${result.orderId}`);
      } else if (result.status === "email_sent") {
        try { localStorage.setItem(LS_EMAIL_KEY, answers["email"] ?? ""); } catch {}
        setEmailSent(true);
      } else if (result.status === "success") {
        try { localStorage.setItem(LS_EMAIL_KEY, answers["email"] ?? ""); } catch {}
        router.push("/thanks");
      } else {
        setSubmitError(result.message ?? "Ошибка при отправке.");
      }
    });
  }

  if (error) {
    return (
      <div className="bg-white rounded-2xl border border-gray-100 p-8 text-center space-y-4">
        <div className="flex justify-center">
          <ServerCrash className="h-10 w-10 text-red-400" aria-hidden="true" />
        </div>
        <h2 className="text-xl font-bold text-gray-900">Не удалось загрузить форму</h2>
        <p className="text-gray-500 text-sm">
          Сервис временно недоступен. Попробуйте обновить страницу или зайдите позже.
        </p>
        <button
          onClick={() => window.location.reload()}
          className="inline-flex items-center gap-2 text-sm font-medium text-primary hover:text-primary/80 underline underline-offset-2 transition-colors"
        >
          Обновить страницу
        </button>
      </div>
    );
  }

  if (emailSent) {
    return (
      <div className="bg-white rounded-2xl border border-gray-100 p-8 text-center space-y-4">
        <div className="text-5xl">📧</div>
        <h2 className="text-xl font-bold text-gray-900">Проверьте почту</h2>
        <p className="text-gray-500 text-sm">
          Мы отправили ссылку на{" "}
          <span className="font-medium text-gray-700">{answers["email"]}</span>
          . Перейдите по ней, чтобы увидеть статус заказа и оплатить.
        </p>
        <p className="text-xs text-gray-400">
          Не нашли? Проверьте папку «Спам» или напишите на{" "}
          <a href="mailto:lawdocsru@gmail.com" className="text-blue-600 hover:underline">
            lawdocsru@gmail.com
          </a>
        </p>
      </div>
    );
  }

  return (
    <div>
      {/* Progress bar */}
      <div className="mb-8">
        <div className="flex justify-between text-xs text-gray-400 mb-2">
          <span>
            Шаг {currentStep + 1} из {steps.length}
          </span>
          <span>{step.title}</span>
        </div>
        <div className="h-1.5 bg-gray-200 rounded-full overflow-hidden">
          <div
            className="h-full bg-blue-600 rounded-full transition-all duration-300"
            style={{ width: `${progressPct}%` }}
          />
        </div>
      </div>

      {/* Step card */}
      <div className="bg-white rounded-2xl border border-gray-100 p-6 md:p-8">
        <h2 className="text-xl font-bold text-gray-900 mb-6">{step.title}</h2>

        <div className="space-y-5">
          {step.fields.map((field) => (
            <FieldRenderer
              key={field.id}
              field={field}
              value={answers[field.id] ?? ""}
              onChange={(v) => handleChange(field.id, v)}
              invalid={invalidFieldIds.includes(field.id)}
            />
          ))}
        </div>

        {fieldErrors.length > 0 && (
          <div className="mt-5 flex items-start gap-2 text-sm text-red-600 bg-red-50 border border-red-200 rounded-lg px-3 py-2">
            <AlertCircle className="h-4 w-4 mt-0.5 shrink-0" />
            <span>
              Заполните обязательные поля:{" "}
              <span className="font-medium">{fieldErrors.join(", ")}</span>
            </span>
          </div>
        )}

        {dateErrors.length > 0 && (
          <div className="mt-5 flex items-start gap-2 text-sm text-red-600 bg-red-50 border border-red-200 rounded-lg px-3 py-2">
            <AlertCircle className="h-4 w-4 mt-0.5 shrink-0" />
            <ul className="space-y-1">
              {dateErrors.map((msg) => (
                <li key={msg}>{msg}</li>
              ))}
            </ul>
          </div>
        )}

        {submitError && (
          <div className="mt-5 flex items-start gap-2 text-sm text-red-600 bg-red-50 border border-red-200 rounded-lg px-3 py-2">
            <AlertCircle className="h-4 w-4 mt-0.5 shrink-0" />
            <span>{submitError}</span>
          </div>
        )}

        {isLast && <ReviewSummary steps={steps} answers={answers} />}

        {isLast && (
          <label
            className={`mt-6 flex items-start gap-3 rounded-lg border px-3 py-3 cursor-pointer transition-colors ${
              consentError ? "border-red-300 bg-red-50" : "border-gray-200 bg-gray-50"
            }`}
          >
            <input
              type="checkbox"
              checked={consentAccepted}
              onChange={(e) => {
                setConsentAccepted(e.target.checked);
                if (e.target.checked) setConsentError(false);
              }}
              className="h-4 w-4 mt-0.5 accent-blue-600 shrink-0"
            />
            <span className="text-sm text-gray-700">
              Я принимаю условия{" "}
              <a
                href="/legal/offer"
                target="_blank"
                rel="noopener noreferrer"
                className="text-blue-600 hover:underline"
              >
                договора-оферты
              </a>{" "}
              и даю согласие на{" "}
              <a
                href="/legal/privacy"
                target="_blank"
                rel="noopener noreferrer"
                className="text-blue-600 hover:underline"
              >
                обработку персональных данных
              </a>
              .
            </span>
          </label>
        )}

        {consentError && (
          <div className="mt-3 flex items-start gap-2 text-sm text-red-600 bg-red-50 border border-red-200 rounded-lg px-3 py-2">
            <AlertCircle className="h-4 w-4 mt-0.5 shrink-0" />
            <span>Чтобы продолжить, подтвердите согласие с офертой и обработкой персональных данных.</span>
          </div>
        )}
      </div>

      {/* Navigation */}
      <div className="flex items-center gap-3 mt-6">
        {!isFirst && (
          <Button
            variant="outline"
            onClick={handleBack}
            disabled={isPending}
            className="h-11 px-5"
          >
            <ChevronLeft className="h-4 w-4 mr-1" />
            Назад
          </Button>
        )}

        <div className="flex-1" />

        {isLast ? (
          <div className="flex flex-col items-end gap-2">
            {/* Кнопка заблокирована, пока не отмечено согласие с офертой и обработкой ПДн. */}
            <Button
              onClick={handleSubmit}
              disabled={isPending || !consentAccepted}
              className="h-11 px-8 text-base"
            >
              {isPending ? (
                <>
                  <Loader2 className="h-4 w-4 mr-2 animate-spin" />
                  Отправляем…
                </>
              ) : (
                "Отправить заявку"
              )}
            </Button>
            <p className="text-xs text-gray-400">
              После оплаты 199 ₽ документ придёт на email в течение нескольких минут
            </p>
          </div>
        ) : (
          <Button onClick={handleNext} className="h-11 px-8 text-base">
            Далее
            <ChevronRight className="h-4 w-4 ml-1" />
          </Button>
        )}
      </div>
    </div>
  );
}

// Человекочитаемое значение поля для сводки: radio → подпись варианта, прочее — как ввели.
function displayValue(field: WizardField, raw: string): string {
  if (field.type === "radio" && field.options) {
    return field.options.find((o) => o.value === raw)?.label ?? raw;
  }
  return raw;
}

// Сводка «что вы ввели» на финальном шаге — пользователь проверяет форму перед отправкой.
function ReviewSummary({
  steps,
  answers,
}: {
  steps: WizardStep[];
  answers: Record<string, string>;
}) {
  const rows: { id: string; label: string; value: string }[] = [];
  for (const s of steps) {
    for (const f of s.fields) {
      const raw = answers[f.id]?.trim();
      if (raw) rows.push({ id: f.id, label: f.label, value: displayValue(f, raw) });
    }
  }
  if (rows.length === 0) return null;

  return (
    <div className="mt-6 rounded-xl border border-gray-200 bg-gray-50 p-4">
      <h3 className="text-sm font-semibold text-gray-900 mb-3">Проверьте введённые данные</h3>
      <dl className="divide-y divide-gray-200">
        {rows.map((r) => (
          <div key={r.id} className="flex gap-3 py-1.5 text-sm">
            <dt className="w-2/5 shrink-0 text-gray-500">{r.label}</dt>
            <dd className="flex-1 text-gray-900 break-words whitespace-pre-wrap">{r.value}</dd>
          </div>
        ))}
      </dl>
    </div>
  );
}

function FieldRenderer({
  field,
  value,
  onChange,
  invalid = false,
}: {
  field: WizardField;
  value: string;
  onChange: (v: string) => void;
  invalid?: boolean;
}) {
  // Красная подсветка для невалидного поля (пустое обязательное / ошибка типа).
  const invalidCls = invalid ? "border-red-400 focus-visible:ring-red-400" : "";
  return (
    <div className="space-y-2">
      <Label htmlFor={field.id} className={invalid ? "text-red-600" : undefined}>
        {field.label}
        {field.required && <span className="text-red-500 ml-1">*</span>}
      </Label>

      {field.type === "radio" && field.options && (
        <div className="space-y-2">
          {field.options.map((opt) => (
            <label
              key={opt.value}
              className={`flex items-center gap-3 p-3 rounded-xl border cursor-pointer transition-colors ${
                value === opt.value
                  ? "border-blue-500 bg-blue-50"
                  : "border-gray-200 hover:border-gray-300 bg-white"
              }`}
            >
              <input
                type="radio"
                name={field.id}
                value={opt.value}
                checked={value === opt.value}
                onChange={() => onChange(opt.value)}
                className="h-4 w-4 accent-blue-600 shrink-0"
              />
              <span className="text-sm text-gray-800">{opt.label}</span>
            </label>
          ))}
        </div>
      )}

      {field.type === "textarea" && (
        <Textarea
          id={field.id}
          value={value}
          onChange={(e) => onChange(e.target.value)}
          placeholder={field.placeholder}
          rows={4}
          className={invalidCls}
        />
      )}

      {field.type === "date" && (
        <Input
          id={field.id}
          type="text"
          inputMode="numeric"
          value={value}
          onChange={(e) => {
            const digits = e.target.value.replace(/\D/g, "").slice(0, 8);
            let formatted = digits;
            if (digits.length > 2) formatted = digits.slice(0, 2) + "." + digits.slice(2);
            if (digits.length > 4) formatted = digits.slice(0, 2) + "." + digits.slice(2, 4) + "." + digits.slice(4);
            onChange(formatted);
          }}
          placeholder="дд.мм.гггг"
          maxLength={10}
          className={invalidCls}
        />
      )}

      {(field.type === "text" || field.type === "number") && (
        <Input
          id={field.id}
          type="text"
          inputMode={field.type === "number" ? "numeric" : undefined}
          value={value}
          // Числовое поле принимает только цифры — нецифровые символы отсекаются на вводе.
          onChange={(e) =>
            onChange(field.type === "number" ? e.target.value.replace(/\D/g, "") : e.target.value)
          }
          placeholder={field.placeholder}
          maxLength={field.max_len ?? undefined}
          className={invalidCls}
        />
      )}

      {field.hint && <p className="text-xs text-gray-400">{field.hint}</p>}
    </div>
  );
}
