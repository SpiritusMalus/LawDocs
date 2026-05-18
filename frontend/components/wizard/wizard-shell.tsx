"use client";

import { useState, useTransition, useEffect } from "react";
import { useRouter } from "next/navigation";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Textarea } from "@/components/ui/textarea";
import { ChevronLeft, ChevronRight, Loader2, AlertCircle, ServerCrash } from "lucide-react";
import type { WizardStep, WizardField } from "@/lib/wizard-types";
import { submitWizard } from "@/lib/actions/submit-wizard";

const LS_EMAIL_KEY = "lawdocs_email";
const CONTACT_FIELDS = ["full_name", "phone", "contact_address", "email"] as const;

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
  const [submitError, setSubmitError] = useState<string | null>(null);
  const [emailSent, setEmailSent] = useState(false);
  const [isPending, startTransition] = useTransition();

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

  function getMissingRequired(): string[] {
    return step.fields
      .filter((f) => f.required && !answers[f.id]?.trim())
      .map((f) => f.label);
  }

  function handleNext() {
    const missing = getMissingRequired();
    if (missing.length > 0) {
      setFieldErrors(missing);
      return;
    }
    setFieldErrors([]);
    setCurrentStep((s) => s + 1);
    window.scrollTo({ top: 0, behavior: "smooth" });
  }

  function handleBack() {
    setFieldErrors([]);
    setSubmitError(null);
    setCurrentStep((s) => s - 1);
    window.scrollTo({ top: 0, behavior: "smooth" });
  }

  function handleChange(fieldId: string, value: string) {
    setAnswers((prev) => ({ ...prev, [fieldId]: value }));
    if (fieldErrors.length > 0) setFieldErrors([]);
  }

  function handleSubmit() {
    const missing = getMissingRequired();
    if (missing.length > 0) {
      setFieldErrors(missing);
      return;
    }
    setSubmitError(null);
    startTransition(async () => {
      const result = await submitWizard({ situationId, answers });
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

        {submitError && (
          <div className="mt-5 flex items-start gap-2 text-sm text-red-600 bg-red-50 border border-red-200 rounded-lg px-3 py-2">
            <AlertCircle className="h-4 w-4 mt-0.5 shrink-0" />
            <span>{submitError}</span>
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
            <Button onClick={handleSubmit} disabled={isPending} className="h-11 px-8 text-base">
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

function FieldRenderer({
  field,
  value,
  onChange,
}: {
  field: WizardField;
  value: string;
  onChange: (v: string) => void;
}) {
  return (
    <div className="space-y-2">
      <Label htmlFor={field.id}>
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
        />
      )}

      {(field.type === "text" || field.type === "number") && (
        <Input
          id={field.id}
          type={field.type === "number" ? "text" : field.type}
          inputMode={field.type === "number" ? "numeric" : undefined}
          value={value}
          onChange={(e) => onChange(e.target.value)}
          placeholder={field.placeholder}
        />
      )}

      {field.hint && <p className="text-xs text-gray-400">{field.hint}</p>}
    </div>
  );
}
