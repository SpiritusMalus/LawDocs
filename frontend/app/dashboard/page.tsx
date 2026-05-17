import type { Metadata } from "next";
import Link from "next/link";
import { cookies } from "next/headers";
import { redirect } from "next/navigation";
import { Scale, FileText, PlusCircle } from "lucide-react";
import { OrderCard } from "@/components/order/order-card";
import { LogoutButton } from "@/components/auth/logout-button";
import { DashboardPoller } from "@/components/dashboard/dashboard-poller";

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
  const hasGenerating = orders.some((o) => o.status === "generating");

  return (
    <main className="min-h-screen bg-gray-50 py-12 px-4">
      <DashboardPoller hasGenerating={hasGenerating} />
      <div className="max-w-2xl mx-auto">
        <div className="flex items-center justify-between mb-8">
          <div className="flex items-center gap-3">
            <Scale className="h-6 w-6 text-primary" />
            <h1 className="text-2xl font-bold text-gray-900">Мои заказы</h1>
          </div>
          <div className="flex items-center gap-3">
            <Link
              href="/situations"
              className="flex items-center gap-1.5 text-sm font-medium text-primary hover:text-primary/80 transition-colors"
            >
              <PlusCircle className="h-4 w-4" />
              Новый документ
            </Link>
            <LogoutButton />
          </div>
        </div>

        {orders.length === 0 ? (
          <div className="bg-white rounded-2xl border border-gray-100 p-12 text-center">
            <FileText className="h-12 w-12 text-gray-200 mx-auto mb-5" />
            <h2 className="text-lg font-semibold text-gray-900 mb-2">Заказов пока нет</h2>
            <p className="text-gray-400 text-sm mb-6 max-w-xs mx-auto">
              Выберите ситуацию, ответьте на несколько вопросов — и получите готовый документ.
            </p>
            <Link
              href="/situations"
              className="inline-flex items-center gap-2 bg-primary hover:bg-primary/90 text-primary-foreground text-sm font-semibold px-5 py-2.5 rounded-xl transition-colors"
            >
              <PlusCircle className="h-4 w-4" />
              Создать первый документ
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
