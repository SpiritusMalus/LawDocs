export type FieldType = "text" | "number" | "date" | "textarea" | "radio";

export interface WizardField {
  id: string;
  type: FieldType;
  label: string;
  placeholder?: string;
  required?: boolean;
  hint?: string;
  options?: { value: string; label: string }[];
}

export interface WizardStep {
  title: string;
  fields: WizardField[];
}
