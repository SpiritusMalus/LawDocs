// Presentational-секции экрана заказа, вынесенные из order-status.tsx (Фаза 4).
// Без собственного состояния: всё приходит пропсами, логика остаётся в OrderStatus.
// JSX перенесён дословно — поведение и вёрстка не меняются.
import Link from "next/link";
import { Download, FileText, Loader2, RefreshCcw, PlusCircle } from "lucide-react";
import { Button } from "@/components/ui/button";
import { ReviewForm } from "@/components/reviews/review-form";
import { RecoverAccessInline } from "@/components/order/recover-access-inline";

interface OrderLike {
  situation_id: string;
  status: string;
  amount: number;
  payment_url: string | null;
}

export function PaySection({
  order,
  isPaying,
  payError,
  onPay,
}: {
  order: OrderLike;
  isPaying: boolean;
  payError: string | null;
  onPay: () => void;
}) {
  return (
    <div className="space-y-3">
      {order.status === "pending_payment" && order.payment_url ? (
        <a
          href={order.payment_url}
          className="w-full h-12 text-base inline-flex items-center justify-center rounded-md bg-primary text-primary-foreground hover:bg-primary/80 font-medium transition-colors"
        >
          Перейти к оплате →
        </a>
      ) : (
        <Button
          onClick={onPay}
          disabled={isPaying}
          className="w-full h-12 text-base"
        >
          {isPaying ? (
            <>
              <Loader2 className="h-4 w-4 mr-2 animate-spin" />
              Перенаправляем…
            </>
          ) : (
            `Оплатить ${(order.amount / 100).toFixed(0)} ₽`
          )}
        </Button>
      )}
      {order.status === "pending_payment" && (
        <button
          onClick={onPay}
          disabled={isPaying}
          className="text-xs text-gray-400 hover:text-gray-600 underline w-full text-center"
        >
          {isPaying ? "Создаём новый платёж…" : "Ссылка устарела? Создать новый платёж"}
        </button>
      )}
      {payError && <p className="text-sm text-red-600">{payError}</p>}
    </div>
  );
}

export function DoneSection({
  orderId,
  order,
  downloadingFmt,
  downloadError,
  onDownload,
  needsKeyFor,
  onRecovered,
}: {
  orderId: string;
  order: OrderLike;
  downloadingFmt: string | null;
  downloadError: string | null;
  onDownload: (fmt: "docx" | "pdf") => void;
  needsKeyFor: "docx" | "pdf" | null;
  onRecovered: () => void;
}) {
  return (
    <>
      <div className="flex flex-col sm:flex-row gap-3">
        <button
          onClick={() => onDownload("docx")}
          disabled={downloadingFmt !== null}
          className="flex-1 flex items-center justify-center gap-2 h-11 rounded-lg border border-gray-200 bg-gray-50 hover:bg-gray-100 text-sm font-medium text-gray-700 transition-colors disabled:opacity-60"
        >
          {downloadingFmt === "docx" ? (
            <Loader2 className="h-4 w-4 animate-spin" />
          ) : (
            <Download className="h-4 w-4" />
          )}
          Скачать Word
        </button>
        <button
          onClick={() => onDownload("pdf")}
          disabled={downloadingFmt !== null}
          className="flex-1 flex items-center justify-center gap-2 h-11 rounded-lg bg-primary hover:bg-primary/90 text-sm font-medium text-primary-foreground transition-colors disabled:opacity-60"
        >
          {downloadingFmt === "pdf" ? (
            <Loader2 className="h-4 w-4 animate-spin" />
          ) : (
            <Download className="h-4 w-4" />
          )}
          Скачать PDF
        </button>
      </div>
      {downloadError && (
        <p className="text-sm text-red-600">{downloadError}</p>
      )}

      {needsKeyFor && <RecoverAccessInline onRecovered={onRecovered} />}

      <a
        href={`/api/documents/${orderId}/download/instruction`}
        download
        className="flex items-center justify-center gap-2 h-11 rounded-lg border border-primary/20 bg-primary/5 hover:bg-primary/10 text-sm font-medium text-primary transition-colors w-full"
      >
        <FileText className="h-4 w-4" />
        Скачать инструкцию (куда подать и что делать дальше)
      </a>

      <p className="text-xs text-gray-400">
        Письмо с ссылкой на заказ отправлено на вашу почту.{" "}
        <a href="mailto:lawdocsru@gmail.com" className="text-primary hover:underline">
          Нужна помощь?
        </a>
      </p>
      <Link
        href="/situations"
        className="inline-flex items-center gap-2 text-sm font-medium text-primary hover:text-primary/80 transition-colors"
      >
        <PlusCircle className="h-4 w-4" />
        Создать ещё один документ
      </Link>
      <div className="border-t border-gray-100 pt-2">
        <ReviewForm orderId={orderId} situationId={order.situation_id} />
      </div>
    </>
  );
}

export function FailedSection({
  order,
  isRetrying,
  retryError,
  onRetry,
}: {
  order: OrderLike;
  isRetrying: boolean;
  retryError: string | null;
  onRetry: () => void;
}) {
  return (
    <div className="flex flex-col gap-3">
      <Button
        onClick={onRetry}
        disabled={isRetrying}
        className="w-full h-11 text-base"
      >
        {isRetrying ? (
          <>
            <Loader2 className="h-4 w-4 mr-2 animate-spin" />
            Запускаем…
          </>
        ) : (
          <>
            <RefreshCcw className="h-4 w-4 mr-2" />
            Попробовать ещё раз
          </>
        )}
      </Button>
      {retryError && <p className="text-sm text-red-600">{retryError}</p>}
      <div className="flex flex-col sm:flex-row gap-3">
        <Link
          href={`/wizard/${order.situation_id}`}
          className="flex-1 flex items-center justify-center gap-2 h-10 rounded-lg border border-gray-200 bg-gray-50 hover:bg-gray-100 text-sm font-medium text-gray-700 transition-colors"
        >
          <RefreshCcw className="h-4 w-4" />
          Заполнить заново
        </Link>
        <a
          href="mailto:lawdocsru@gmail.com"
          className="flex-1 flex items-center justify-center gap-2 h-10 rounded-lg bg-primary hover:bg-primary/90 text-sm font-medium text-primary-foreground transition-colors"
        >
          Написать в поддержку
        </a>
      </div>
    </div>
  );
}

export function RefundedSection({ order }: { order: OrderLike }) {
  return (
    <div className="flex flex-col gap-3">
      <p className="text-sm text-gray-500">
        Возврат {(order.amount / 100).toFixed(0)} ₽. Если хотите попробовать ещё раз — заполните форму заново, оплата спишется только при успешной генерации.
      </p>
      <div className="flex flex-col sm:flex-row gap-3">
        <Link
          href={`/wizard/${order.situation_id}`}
          className="flex-1 flex items-center justify-center gap-2 h-10 rounded-lg border border-gray-200 bg-gray-50 hover:bg-gray-100 text-sm font-medium text-gray-700 transition-colors"
        >
          <RefreshCcw className="h-4 w-4" />
          Заполнить заново
        </Link>
        <a
          href="mailto:lawdocsru@gmail.com"
          className="flex-1 flex items-center justify-center gap-2 h-10 rounded-lg bg-primary hover:bg-primary/90 text-sm font-medium text-primary-foreground transition-colors"
        >
          Написать в поддержку
        </a>
      </div>
    </div>
  );
}
