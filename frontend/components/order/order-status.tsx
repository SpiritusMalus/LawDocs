"use client";

import { useEffect, useState } from "react";
import { CheckCircle, Clock, Download, FileText, Loader2, XCircle, Info, RefreshCcw, PlusCircle } from "lucide-react";
import Link from "next/link";
import { Button } from "@/components/ui/button";

interface Order {
  id: string;
  situation_id: string;
  status: string;
  amount: number;
  created_at: string;
  paid_at: string | null;
}

type StatusConfig = {
  icon: React.ReactNode;
  label: string;
  description: string;
  terminal: boolean;
};

const STATUS_CONFIG: Record<string, StatusConfig> = {
  draft: {
    icon: <Clock className="h-8 w-8 text-gray-400" />,
    label: "Ожидание оплаты",
    description: "Нажмите кнопку ниже, чтобы оплатить и запустить создание документа.",
    terminal: false,
  },
  pending_payment: {
    icon: <Clock className="h-8 w-8 text-yellow-500" />,
    label: "Ожидание оплаты",
    description: "Ожидаем подтверждения платежа от банка.",
    terminal: false,
  },
  paid: {
    icon: <CheckCircle className="h-8 w-8 text-green-500" />,
    label: "Оплачено",
    description: "Оплата получена. Начинаем подготовку документа.",
    terminal: false,
  },
  generating: {
    icon: <Loader2 className="h-8 w-8 text-blue-500 animate-spin" />,
    label: "Создаём документ",
    description: "Документ готовится — обычно это занимает меньше минуты.",
    terminal: false,
  },
  done: {
    icon: <FileText className="h-8 w-8 text-green-600" />,
    label: "Документ готов",
    description: "Документ отправлен на вашу почту и доступен для скачивания.",
    terminal: true,
  },
  failed: {
    icon: <XCircle className="h-8 w-8 text-red-500" />,
    label: "Ошибка генерации",
    description: "Что-то пошло не так. Мы уже получили уведомление — проверьте почту или напишите нам.",
    terminal: true,
  },
};

const POLL_STATUSES = new Set(["paid", "generating"]);

const SEND_INSTRUCTIONS: Record<string, string> = {
  shop: "Направьте претензию заказным письмом с уведомлением или лично под роспись в магазин. Срок ответа — 10 дней.",
  marketplace: "Отправьте претензию через форму обратной связи маркетплейса и продублируйте заказным письмом на юридический адрес. Срок ответа — 10 дней.",
  bank: "Подайте заявление в отделении банка под роспись или отправьте заказным письмом. Срок ответа — 30 дней.",
  employer: "Вручите претензию лично под роспись или отправьте заказным письмом на адрес организации. Срок ответа — 3 рабочих дня.",
  insurance: "Отправьте претензию заказным письмом или через личный кабинет страховой. По закону ответ обязателен в течение 10 рабочих дней.",
  utility: "Подайте претензию в УК лично под роспись (получите свой экземпляр) или отправьте заказным письмом. Срок ответа — 30 дней.",
  airline: "Направьте претензию через официальный сайт авиакомпании или заказным письмом. Срок ответа — 30 дней.",
};

export function OrderStatus({
  orderId,
  initialOrder,
}: {
  orderId: string;
  initialOrder: Order;
}) {
  const [order, setOrder] = useState<Order>(initialOrder);
  const [payError, setPayError] = useState<string | null>(null);
  const [isPaying, setIsPaying] = useState(false);

  // Poll status while processing
  useEffect(() => {
    if (!POLL_STATUSES.has(order.status)) return;

    const interval = setInterval(async () => {
      try {
        const res = await fetch(`/api/orders/${orderId}`, { cache: "no-store" });
        if (res.ok) {
          const data: Order = await res.json();
          setOrder(data);
          if (!POLL_STATUSES.has(data.status)) clearInterval(interval);
        }
      } catch {
        // network blip — keep polling
      }
    }, 4000);

    return () => clearInterval(interval);
  }, [orderId, order.status]);

  async function handlePay() {
    setIsPaying(true);
    setPayError(null);
    try {
      const res = await fetch(`/api/orders/${orderId}/pay`, { method: "POST" });
      const data = await res.json();
      if (!res.ok) {
        setPayError(data.error ?? "Ошибка при создании платежа. Попробуйте ещё раз.");
        return;
      }
      window.location.href = data.payment_url;
    } catch {
      setPayError("Не удалось создать платёж. Попробуйте позже или напишите на hi@lawdocs.ru.");
    } finally {
      setIsPaying(false);
    }
  }

  const cfg = STATUS_CONFIG[order.status] ?? STATUS_CONFIG["failed"]!;

  return (
    <div className="bg-white rounded-2xl border border-gray-100 p-8 text-center space-y-6">
      <div className="flex justify-center">{cfg.icon}</div>

      <div>
        <p className="text-lg font-semibold text-gray-900">{cfg.label}</p>
        <p className="text-gray-500 text-sm mt-1">{cfg.description}</p>
      </div>

      {order.status === "draft" && (
        <div className="space-y-3">
          <Button
            onClick={handlePay}
            disabled={isPaying}
            className="w-full h-12 text-base"
          >
            {isPaying ? (
              <>
                <Loader2 className="h-4 w-4 mr-2 animate-spin" />
                Перенаправляем…
              </>
            ) : (
              "Оплатить 500 ₽"
            )}
          </Button>
          {payError && <p className="text-sm text-red-600">{payError}</p>}
        </div>
      )}

      {order.status === "done" && (
        <div className="flex flex-col sm:flex-row gap-3">
          <a
            href={`/api/documents/${orderId}/download/docx`}
            download="document.docx"
            className="flex-1 flex items-center justify-center gap-2 h-11 rounded-lg border border-gray-200 bg-gray-50 hover:bg-gray-100 text-sm font-medium text-gray-700 transition-colors"
          >
            <Download className="h-4 w-4" />
            Скачать Word
          </a>
          <a
            href={`/api/documents/${orderId}/download/pdf`}
            download="document.pdf"
            className="flex-1 flex items-center justify-center gap-2 h-11 rounded-lg bg-blue-600 hover:bg-blue-700 text-sm font-medium text-white transition-colors"
          >
            <Download className="h-4 w-4" />
            Скачать PDF
          </a>
        </div>
      )}

      {order.status === "done" && SEND_INSTRUCTIONS[order.situation_id] && (
        <div className="text-left bg-blue-50 border border-blue-100 rounded-xl p-4">
          <div className="flex items-start gap-2">
            <Info className="h-4 w-4 text-blue-500 mt-0.5 shrink-0" />
            <div>
              <p className="text-xs font-semibold text-blue-700 mb-1">Что делать дальше</p>
              <p className="text-xs text-blue-700">{SEND_INSTRUCTIONS[order.situation_id]}</p>
            </div>
          </div>
        </div>
      )}

      {order.status === "done" && (
        <>
          <p className="text-xs text-gray-400">
            PDF также отправлен на вашу почту.{" "}
            <a href="mailto:hi@lawdocs.ru" className="text-blue-600 hover:underline">
              Не получили?
            </a>
          </p>
          <Link
            href="/situations"
            className="inline-flex items-center gap-2 text-sm font-medium text-blue-600 hover:text-blue-700 transition-colors"
          >
            <PlusCircle className="h-4 w-4" />
            Создать ещё один документ
          </Link>
        </>
      )}

      {order.status === "failed" && (
        <div className="flex flex-col sm:flex-row gap-3">
          <Link
            href={`/wizard/${order.situation_id}`}
            className="flex-1 flex items-center justify-center gap-2 h-10 rounded-lg border border-gray-200 bg-gray-50 hover:bg-gray-100 text-sm font-medium text-gray-700 transition-colors"
          >
            <RefreshCcw className="h-4 w-4" />
            Заполнить заново
          </Link>
          <a
            href="mailto:hi@lawdocs.ru"
            className="flex-1 flex items-center justify-center gap-2 h-10 rounded-lg bg-blue-600 hover:bg-blue-700 text-sm font-medium text-white transition-colors"
          >
            Написать в поддержку
          </a>
        </div>
      )}

      <p className="text-xs text-gray-300">
        Заказ № {orderId.slice(0, 8).toUpperCase()}
      </p>
    </div>
  );
}
