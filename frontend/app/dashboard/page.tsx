import type { Metadata } from "next";
import Link from "next/link";
import { cookies } from "next/headers";
import { redirect } from "next/navigation";
import { Scale, FileText, PlusCircle } from "lucide-react";
import { OrderCard } from "@/components/order/order-card";
import { LogoutButton } from "@/components/auth/logout-button";

export const metadata: Metadata = {
  title: "Мои заказы — LawDocs",
  robots: { index: false },
};

interface OrderItem {
  id: string;
  situation_id: string;
  status: string;
  amount: number;
  created_at: string;
  has_document: boolean;
}

async function fetchOrders(token: string): Promise<OrderItem[]> {
  const backendUrl = process.env.BACKEND_URL;
  if (!backendUrl) return [];

  try {
    const res = await fetch(`${backendUrl}/api/v1/orders/`, {
      headers: { Authorization: `Bearer ${token}` },
      cache: "no-store",
    });
    if (!res.ok) return [];
    return (await res.json()) as OrderItem[];
  } catch {
    return [];
  }
}

export default async function DashboardPage() {
  const cookieStore = await cookies();
  const token = cookieStore.get("access_token")?.value;
  if (!token) redirect("/auth/error?reason=unauthorized");

  const orders = await fetchOrders(token);

  return (
    <main className="min-h-screen bg-gray-50 py-12 px-4">
      <div className="max-w-2xl mx-auto">
        <div className="flex items-center justify-between mb-8">
          <div className="flex items-center gap-3">
            <Scale className="h-6 w-6 text-blue-600" />
            <h1 className="text-2xl font-bold text-gray-900">Мои заказы</h1>
          </div>
          <div className="flex items-center gap-3">
            <Link
              href="/situations"
              className="flex items-center gap-1.5 text-sm font-medium text-blue-600 hover:text-blue-700 transition-colors"
            >
              <PlusCircle className="h-4 w-4" />
              Новый документ
            </Link>
            <LogoutButton />
          </div>
        </div>

        {orders.length === 0 ? (
          <div className="bg-white rounded-2xl border border-gray-100 p-12 text-center">
            <FileText className="h-10 w-10 text-gray-200 mx-auto mb-4" />
            <p className="text-gray-500 text-sm">У вас пока нет заказов.</p>
            <Link
              href="/"
              className="mt-4 inline-block text-sm text-blue-600 hover:underline"
            >
              Перейти на главную
            </Link>
          </div>
        ) : (
          <div className="flex flex-col gap-4">
            {orders.map((order) => (
              <OrderCard key={order.id} order={order} />
            ))}
          </div>
        )}
      </div>
    </main>
  );
}
