export type FieldType = "text" | "number" | "date" | "textarea" | "radio";

export interface WizardField {
  id: string;
  type: FieldType;
  label: string;
  placeholder?: string;
  required?: boolean;
  hint?: string;
  options?: { value: string; label: string }[];
  // Декларативная валидация дат (зеркало backend WizardField).
  not_future?: boolean;
  min_field?: string | null;
  max_field?: string | null;
  max_len?: number | null;
  // Условная видимость: поле показывается, только если значение поля `field`
  // входит в `values`. Иначе скрыто и не участвует в валидации/отправке.
  show_if?: { field: string; values: string[] } | null;
}

export interface WizardStep {
  title: string;
  fields: WizardField[];
}
