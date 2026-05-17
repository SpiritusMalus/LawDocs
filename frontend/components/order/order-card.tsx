import Link from "next/link";
import { Download, FileText, Clock, Loader2, XCircle, CheckCircle } from "lucide-react";

interface OrderItem {
  id: string;
  situation_id: string;
  status: string;
  amount: number;
  created_at: string;
  has_document: boolean;
}

const SITUATION_TITLES: Record<string, string> = {
  shop: "Магазин не возвращает деньги",
  marketplace: "Проблема с маркетплейсом",
  bank: "Банк списал лишнее",
  employer: "Работодатель не выплатил",
  insurance: "Страховая занизила выплату",
  utility: "УК / ЖКХ",
  airline: "Задержка или отмена рейса",
  other: "Другая ситуация",
};

const STATUS_BADGE: Record<string, { label: string; className: string }> = {
  draft: { label: "Ожидает оплаты", className: "bg-gray-100 text-gray-600" },
  pending_payment: { label: "Ожидает оплаты", className: "bg-yellow-100 text-yellow-700" },
  paid: { label: "Оплачен", className: "bg-green-100 text-green-700" },
  generating: { label: "Создаётся…", className: "bg-blue-100 text-blue-700" },
  done: { label: "Готов", className: "bg-green-100 text-green-700" },
  failed: { label: "Ошибка", className: "bg-red-100 text-red-700" },
};

const STATUS_ICON: Record<string, React.ReactNode> = {
  draft: <Clock className="h-5 w-5 text-gray-400" />,
  pending_payment: <Clock className="h-5 w-5 text-yellow-500" />,
  paid: <CheckCircle className="h-5 w-5 text-green-500" />,
  generating: <Loader2 className="h-5 w-5 text-blue-500 animate-spin" />,
  done: <FileText className="h-5 w-5 text-green-600" />,
  failed: <XCircle className="h-5 w-5 text-red-500" />,
};

function formatDate(iso: string) {
  return new Date(iso).toLocaleDateString("ru-RU", {
    day: "numeric",
    month: "long",
    year: "numeric",
  });
}

export function OrderCard({ order }: { order: OrderItem }) {
  const badge = STATUS_BADGE[order.status] ?? STATUS_BADGE["failed"]!;
  const icon = STATUS_ICON[order.status] ?? STATUS_ICON["failed"]!;
  const title = SITUATION_TITLES[order.situation_id] ?? order.situation_id;

  return (
    <div className="bg-white rounded-2xl border border-gray-100 p-5 flex flex-col gap-4">
      <div className="flex items-start gap-3">
        <div className="mt-0.5 shrink-0">{icon}</div>
        <div className="flex-1 min-w-0">
          <p className="font-medium text-gray-900 truncate">{title}</p>
          <p className="text-sm text-gray-400 mt-0.5">{formatDate(order.created_at)}</p>
        </div>
        <span
          className={`shrink-0 text-xs font-medium px-2.5 py-1 rounded-full ${badge.className}`}
        >
          {badge.label}
        </span>
      </div>

      <div className="flex items-center justify-between gap-3 pt-1 border-t border-gray-50">
        <Link
          href={`/orders/${order.id}`}
          className="text-sm text-primary hover:underline"
        >
          Открыть заказ
        </Link>

        {order.has_document && (
          <div className="flex gap-2">
            <a
              href={`/api/documents/${order.id}/download/docx`}
              download="document.docx"
              className="flex items-center gap-1 text-xs font-medium text-gray-600 hover:text-gray-900 border border-gray-200 rounded-lg px-2.5 py-1.5 bg-gray-50 hover:bg-gray-100 transition-colors"
            >
              <Download className="h-3.5 w-3.5" />
              Word
            </a>
            <a
              href={`/api/documents/${order.id}/download/pdf`}
              download="document.pdf"
              className="flex items-center gap-1 text-xs font-medium text-primary-foreground bg-primary hover:bg-primary/90 rounded-lg px-2.5 py-1.5 transition-colors"
            >
              <Download className="h-3.5 w-3.5" />
              PDF
            </a>
          </div>
        )}
      </div>
    </div>
  );
}
