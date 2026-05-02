import type { SituationId } from "./situations";

export type WizardSituationId = Exclude<SituationId, "other">;

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

const CONTACT_STEP: WizardStep = {
  title: "Ваши контакты",
  fields: [
    {
      id: "full_name",
      type: "text",
      label: "ФИО",
      placeholder: "Иванов Иван Иванович",
      required: true,
    },
    {
      id: "contact_address",
      type: "text",
      label: "Адрес проживания",
      placeholder: "г. Москва, ул. Пушкина, д. 1, кв. 5",
      required: true,
      hint: "Нужен для шапки претензии",
    },
    {
      id: "phone",
      type: "text",
      label: "Телефон",
      placeholder: "+7 999 123-45-67",
      required: true,
    },
    {
      id: "email",
      type: "text",
      label: "Email",
      placeholder: "ivan@mail.ru",
      required: true,
      hint: "Готовый документ пришлём сюда",
    },
  ],
};

export const WIZARD_STEPS: Record<WizardSituationId, WizardStep[]> = {
  shop: [
    {
      title: "Магазин и покупка",
      fields: [
        {
          id: "store_name",
          type: "text",
          label: "Название магазина",
          placeholder: "М.Видео, DNS, Спортмастер…",
          required: true,
        },
        {
          id: "store_address",
          type: "text",
          label: "Адрес магазина или сайт",
          placeholder: "ул. Ленина, 1 или www.mvideo.ru",
        },
        {
          id: "product_name",
          type: "text",
          label: "Что купили",
          placeholder: "Смартфон Samsung Galaxy S24",
          required: true,
        },
        {
          id: "product_price",
          type: "number",
          label: "Стоимость, ₽",
          placeholder: "35000",
          required: true,
        },
        {
          id: "purchase_date",
          type: "date",
          label: "Дата покупки",
          required: true,
        },
      ],
    },
    {
      title: "Что случилось",
      fields: [
        {
          id: "problem_type",
          type: "radio",
          label: "Тип проблемы",
          required: true,
          options: [
            { value: "defect", label: "Товар оказался некачественным / сломался" },
            { value: "return14", label: "Отказывают в возврате в 14-дневный срок" },
            { value: "warranty", label: "Проблема с гарантийным ремонтом" },
            { value: "other", label: "Другое" },
          ],
        },
        {
          id: "problem_desc",
          type: "textarea",
          label: "Опишите подробнее",
          placeholder: "Что именно сломалось или в чём отказывают",
          required: true,
        },
        {
          id: "appeal_date",
          type: "date",
          label: "Когда обратились в магазин",
        },
        {
          id: "store_response",
          type: "textarea",
          label: "Что ответил магазин",
          placeholder: "Отказали, сославшись на…",
        },
      ],
    },
    {
      title: "Что вы хотите",
      fields: [
        {
          id: "demand",
          type: "radio",
          label: "Ваше требование",
          required: true,
          options: [
            { value: "refund", label: "Вернуть деньги" },
            { value: "replace", label: "Заменить товар" },
            { value: "repair", label: "Провести гарантийный ремонт" },
            { value: "other", label: "Другое" },
          ],
        },
        {
          id: "penalty_start_date",
          type: "date",
          label: "Дата начала неустойки",
          hint: "Обычно — дата отказа магазина или дата обращения",
        },
      ],
    },
    CONTACT_STEP,
  ],

  marketplace: [
    {
      title: "Маркетплейс и заказ",
      fields: [
        {
          id: "platform",
          type: "radio",
          label: "Маркетплейс",
          required: true,
          options: [
            { value: "wildberries", label: "Wildberries" },
            { value: "ozon", label: "Ozon" },
            { value: "yandex_market", label: "Яндекс.Маркет" },
            { value: "other", label: "Другой" },
          ],
        },
        {
          id: "platform_other",
          type: "text",
          label: "Другой маркетплейс (название)",
          placeholder: "AliExpress, СберМегаМаркет…",
        },
        {
          id: "product_name",
          type: "text",
          label: "Название товара",
          placeholder: "Кроссовки Nike Air Max",
          required: true,
        },
        {
          id: "order_number",
          type: "text",
          label: "Номер заказа",
          placeholder: "12345678",
        },
        {
          id: "order_amount",
          type: "number",
          label: "Сумма заказа, ₽",
          placeholder: "5990",
          required: true,
        },
        {
          id: "order_date",
          type: "date",
          label: "Дата заказа",
        },
      ],
    },
    {
      title: "Что случилось",
      fields: [
        {
          id: "problem_type",
          type: "radio",
          label: "Тип проблемы",
          required: true,
          options: [
            { value: "penalty", label: "Незаконный штраф за «подмену товара»" },
            { value: "paid_return", label: "Взяли деньги за возврат качественного товара" },
            { value: "lost", label: "Потеряли заказ на складе или ПВЗ" },
            { value: "defect", label: "Товар пришёл с дефектом, отказывают в возврате" },
            { value: "other", label: "Другое" },
          ],
        },
        {
          id: "incident_date",
          type: "date",
          label: "Дата события",
        },
        {
          id: "withheld_amount",
          type: "number",
          label: "Спорная / удержанная сумма, ₽",
          placeholder: "1500",
        },
        {
          id: "problem_desc",
          type: "textarea",
          label: "Опишите ситуацию",
          placeholder: "Что именно произошло, что вам сказали",
          required: true,
        },
      ],
    },
    {
      title: "Что вы хотите",
      fields: [
        {
          id: "demand",
          type: "radio",
          label: "Ваше требование",
          required: true,
          options: [
            { value: "return_money", label: "Вернуть удержанную сумму" },
            { value: "refund_order", label: "Вернуть деньги за весь заказ" },
            { value: "cancel_penalty", label: "Отменить штраф" },
            { value: "other", label: "Другое" },
          ],
        },
      ],
    },
    CONTACT_STEP,
  ],

  bank: [
    {
      title: "Банк и ситуация",
      fields: [
        {
          id: "bank_name",
          type: "text",
          label: "Название банка",
          placeholder: "Сбербанк, ВТБ, Тинькофф…",
          required: true,
        },
        {
          id: "violation_type",
          type: "radio",
          label: "Тип нарушения",
          required: true,
          options: [
            { value: "insurance", label: "Навязали страховку к кредиту" },
            { value: "block", label: "Заблокировали счёт или карту по 115-ФЗ" },
            { value: "commission", label: "Незаконная комиссия или списание" },
            { value: "other", label: "Другое" },
          ],
        },
        {
          id: "contract_number",
          type: "text",
          label: "Номер договора или счёта",
          placeholder: "№ 12345678",
        },
        {
          id: "violation_date",
          type: "date",
          label: "Дата события",
        },
      ],
    },
    {
      title: "Детали и сумма",
      fields: [
        {
          id: "amount",
          type: "number",
          label: "Спорная сумма, ₽",
          placeholder: "45000",
          required: true,
        },
        {
          id: "problem_desc",
          type: "textarea",
          label: "Опишите ситуацию",
          placeholder: "Что именно произошло, что говорит банк",
          required: true,
        },
      ],
    },
    {
      title: "Что вы хотите",
      fields: [
        {
          id: "demand",
          type: "radio",
          label: "Ваше требование",
          required: true,
          options: [
            { value: "return_insurance", label: "Вернуть страховую премию" },
            { value: "unblock", label: "Разблокировать счёт / карту" },
            { value: "return_commission", label: "Вернуть незаконную комиссию" },
            { value: "other", label: "Другое" },
          ],
        },
      ],
    },
    CONTACT_STEP,
  ],

  employer: [
    {
      title: "Работодатель",
      fields: [
        {
          id: "company_name",
          type: "text",
          label: "Название организации",
          placeholder: "ООО «Ромашка»",
          required: true,
        },
        {
          id: "company_inn",
          type: "text",
          label: "ИНН работодателя (если знаете)",
          placeholder: "7712345678",
        },
        {
          id: "director_name",
          type: "text",
          label: "ФИО директора (если знаете)",
          placeholder: "Петров Пётр Петрович",
        },
        {
          id: "company_address",
          type: "text",
          label: "Адрес организации",
          placeholder: "г. Москва, ул. Ленина, 1",
        },
      ],
    },
    {
      title: "Трудовые отношения",
      fields: [
        {
          id: "position",
          type: "text",
          label: "Ваша должность",
          placeholder: "Менеджер по продажам",
          required: true,
        },
        {
          id: "hire_date",
          type: "date",
          label: "Дата приёма на работу",
        },
        {
          id: "violation_type",
          type: "radio",
          label: "Тип нарушения",
          required: true,
          options: [
            { value: "salary_delay", label: "Задержка зарплаты" },
            { value: "underpayment", label: "Недоплата / неполный расчёт" },
            { value: "dismissal", label: "Незаконное увольнение" },
            { value: "vacation", label: "Не выплатили отпускные / компенсацию" },
            { value: "other", label: "Другое" },
          ],
        },
        {
          id: "debt_amount",
          type: "number",
          label: "Сумма долга, ₽",
          placeholder: "75000",
          required: true,
        },
        {
          id: "debt_period",
          type: "text",
          label: "За какой период",
          placeholder: "Январь–март 2025",
        },
        {
          id: "last_payment_date",
          type: "date",
          label: "Дата последней выплаты",
        },
      ],
    },
    {
      title: "Что вы хотите",
      fields: [
        {
          id: "demand",
          type: "radio",
          label: "Ваше требование",
          required: true,
          options: [
            { value: "pay_debt", label: "Выплатить долг и компенсацию" },
            { value: "reinstate", label: "Восстановить на работе" },
            { value: "other", label: "Другое" },
          ],
        },
        {
          id: "additional_desc",
          type: "textarea",
          label: "Дополнительные обстоятельства",
          placeholder: "Что важно учесть при составлении претензии",
        },
      ],
    },
    CONTACT_STEP,
  ],

  insurance: [
    {
      title: "Страховая и полис",
      fields: [
        {
          id: "insurance_company",
          type: "text",
          label: "Страховая компания",
          placeholder: "РЕСО, Согаз, Альфастрахование…",
          required: true,
        },
        {
          id: "policy_type",
          type: "radio",
          label: "Тип полиса",
          required: true,
          options: [
            { value: "osago", label: "ОСАГО" },
            { value: "kasko", label: "КАСКО" },
            { value: "other", label: "Другой вид страхования" },
          ],
        },
        {
          id: "policy_number",
          type: "text",
          label: "Номер полиса",
          placeholder: "XXX 1234567890",
        },
      ],
    },
    {
      title: "Страховой случай",
      fields: [
        {
          id: "incident_type",
          type: "radio",
          label: "Тип нарушения",
          required: true,
          options: [
            { value: "underestimate", label: "Занизили сумму выплаты" },
            { value: "refusal", label: "Отказали в страховой выплате" },
            { value: "delay", label: "Нарушили срок выплаты (более 20 раб. дней)" },
          ],
        },
        {
          id: "incident_date",
          type: "date",
          label: "Дата ДТП / страхового события",
          required: true,
        },
        {
          id: "incident_desc",
          type: "textarea",
          label: "Опишите обстоятельства",
          placeholder: "Что произошло, кто виновник (для ОСАГО)",
          required: true,
        },
      ],
    },
    {
      title: "Суммы и требование",
      fields: [
        {
          id: "actual_damage",
          type: "number",
          label: "Реальный ущерб по экспертизе, ₽",
          placeholder: "180000",
        },
        {
          id: "paid_amount",
          type: "number",
          label: "Страховая выплатила, ₽",
          placeholder: "90000",
          hint: "0 — если отказали полностью",
        },
        {
          id: "overdue_days",
          type: "number",
          label: "Дней просрочки (если есть)",
          placeholder: "45",
        },
        {
          id: "demand",
          type: "radio",
          label: "Ваше требование",
          required: true,
          options: [
            { value: "pay_difference", label: "Доплатить разницу и неустойку" },
            { value: "full_payment", label: "Выплатить полную сумму (при отказе)" },
            { value: "other", label: "Другое" },
          ],
        },
      ],
    },
    CONTACT_STEP,
  ],

  utility: [
    {
      title: "УК / ТСЖ и адрес",
      fields: [
        {
          id: "company_name",
          type: "text",
          label: "Название УК или ТСЖ",
          placeholder: "ООО «УК Комфорт»",
          required: true,
        },
        {
          id: "company_address",
          type: "text",
          label: "Адрес УК (офис, если знаете)",
          placeholder: "г. Москва, ул. Ленина, 2",
        },
        {
          id: "apartment_address",
          type: "text",
          label: "Адрес вашей квартиры",
          placeholder: "г. Москва, ул. Пушкина, д. 10, кв. 5",
          required: true,
        },
      ],
    },
    {
      title: "Что случилось",
      fields: [
        {
          id: "violation_type",
          type: "radio",
          label: "Тип нарушения",
          required: true,
          options: [
            { value: "overcharge", label: "Лишние начисления / завышенные тарифы" },
            { value: "poor_service", label: "Некачественные коммунальные услуги" },
            { value: "no_repair", label: "Отказывают делать ремонт общего имущества" },
            { value: "other", label: "Другое" },
          ],
        },
        {
          id: "violation_period",
          type: "text",
          label: "Период нарушения",
          placeholder: "Январь–март 2025",
        },
        {
          id: "problem_desc",
          type: "textarea",
          label: "Опишите проблему",
          placeholder: "Что именно происходит, сколько раз обращались",
          required: true,
        },
        {
          id: "disputed_amount",
          type: "number",
          label: "Сумма к перерасчёту, ₽ (если известна)",
          placeholder: "3200",
        },
      ],
    },
    {
      title: "Что вы хотите",
      fields: [
        {
          id: "demand",
          type: "radio",
          label: "Ваше требование",
          required: true,
          options: [
            { value: "recalculate", label: "Произвести перерасчёт" },
            { value: "fix", label: "Устранить нарушения" },
            { value: "both", label: "И перерасчёт, и устранить нарушения" },
          ],
        },
      ],
    },
    CONTACT_STEP,
  ],

  airline: [
    {
      title: "Рейс",
      fields: [
        {
          id: "airline",
          type: "text",
          label: "Авиакомпания",
          placeholder: "Аэрофлот, S7, Победа…",
          required: true,
        },
        {
          id: "flight_number",
          type: "text",
          label: "Номер рейса",
          placeholder: "SU 1234",
        },
        {
          id: "route",
          type: "text",
          label: "Маршрут",
          placeholder: "Москва (SVO) → Сочи (AER)",
          required: true,
        },
        {
          id: "flight_date",
          type: "date",
          label: "Дата вылета",
          required: true,
        },
      ],
    },
    {
      title: "Что случилось",
      fields: [
        {
          id: "violation_type",
          type: "radio",
          label: "Тип нарушения",
          required: true,
          options: [
            { value: "delay", label: "Задержка рейса" },
            { value: "cancellation", label: "Отмена рейса" },
            { value: "luggage", label: "Утрата или повреждение багажа" },
            { value: "refund_denied", label: "Отказывают вернуть деньги за билет" },
            { value: "other", label: "Другое" },
          ],
        },
        {
          id: "delay_hours",
          type: "number",
          label: "Задержка (часов)",
          placeholder: "5",
          hint: "Заполните, если была задержка",
        },
        {
          id: "problem_desc",
          type: "textarea",
          label: "Опишите ситуацию",
          placeholder: "Что произошло, как реагировала авиакомпания",
          required: true,
        },
      ],
    },
    {
      title: "Суммы и требование",
      fields: [
        {
          id: "ticket_price",
          type: "number",
          label: "Стоимость билета(ов), ₽",
          placeholder: "12500",
          required: true,
        },
        {
          id: "extra_expenses",
          type: "number",
          label: "Доп. расходы (гостиница, такси, новый билет), ₽",
          placeholder: "8000",
        },
        {
          id: "received_compensation",
          type: "number",
          label: "Уже получили от авиакомпании, ₽",
          placeholder: "0",
          hint: "0 — если ничего не дали",
        },
        {
          id: "demand",
          type: "radio",
          label: "Ваше требование",
          required: true,
          options: [
            { value: "compensation", label: "Компенсацию за задержку" },
            { value: "refund", label: "Возврат стоимости билета" },
            { value: "expenses", label: "Возмещение доп. расходов" },
            { value: "all", label: "Всё вместе" },
          ],
        },
      ],
    },
    CONTACT_STEP,
  ],
};
