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
}

export interface WizardStep {
  title: string;
  fields: WizardField[];
}
