"use client";

import { useState, useTransition } from "react";
import { useRouter } from "next/navigation";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Textarea } from "@/components/ui/textarea";
import { ChevronLeft, ChevronRight, Loader2, AlertCircle } from "lucide-react";
import type { WizardSituationId, WizardStep, WizardField } from "@/lib/wizard-questions";
import { submitWizard } from "@/lib/actions/submit-wizard";

interface WizardShellProps {
  steps: WizardStep[];
  situationId: WizardSituationId;
}

export function WizardShell({ steps, situationId }: WizardShellProps) {
  const router = useRouter();
  const [currentStep, setCurrentStep] = useState(0);
  const [answers, setAnswers] = useState<Record<string, string>>({});
  const [fieldErrors, setFieldErrors] = useState<string[]>([]);
  const [submitError, setSubmitError] = useState<string | null>(null);
  const [isPending, startTransition] = useTransition();

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
      if (result.status === "success") {
        router.push("/thanks");
      } else {
        setSubmitError(result.message ?? "Ошибка при отправке.");
      }
    });
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
              Свяжемся в течение 2 часов и выставим счёт на 500&nbsp;₽
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

      {(field.type === "text" || field.type === "number" || field.type === "date") && (
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
