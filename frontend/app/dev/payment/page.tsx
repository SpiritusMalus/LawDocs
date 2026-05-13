/**
 * Dev-only payment simulation page.
 * ЮKassa stub in payment.py redirects here when YOOKASSA_SHOP_ID is not set.
 * Simulates webhook call so the full flow can be tested locally.
 */

import { notFound } from "next/navigation";
import { DevPaymentForm } from "./dev-payment-form";

export default async function DevPaymentPage({
  searchParams,
}: {
  searchParams: Promise<{ order_id?: string }>;
}) {
  if (process.env.APP_ENV === "production") notFound();

  const { order_id } = await searchParams;
  if (!order_id) notFound();

  return (
    <main className="min-h-screen bg-gray-100 flex items-center justify-center px-4">
      <div className="bg-white rounded-2xl border border-gray-200 p-8 max-w-sm w-full text-center space-y-6">
        <div>
          <div className="text-4xl mb-3">🏦</div>
          <h1 className="text-xl font-bold text-gray-900">Dev-платёж</h1>
          <p className="text-sm text-gray-400 mt-1">Это тестовая страница — замена ЮKassa</p>
        </div>

        <div className="bg-gray-50 rounded-xl p-4 text-left space-y-1">
          <p className="text-xs text-gray-400 uppercase tracking-wide">Заказ</p>
          <p className="font-mono text-sm text-gray-700">{order_id}</p>
          <p className="text-lg font-bold text-gray-900 mt-2">100 ₽</p>
        </div>

        <DevPaymentForm orderId={order_id} />
      </div>
    </main>
  );
}
