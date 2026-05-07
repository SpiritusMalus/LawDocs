import type { Metadata } from "next";
import Link from "next/link";
import { cookies } from "next/headers";
import { notFound, redirect } from "next/navigation";
import { ChevronRight } from "lucide-react";
import { OrderStatus } from "@/components/order/order-status";

export const metadata: Metadata = {
  title: "Ваш заказ — LawDocs",
  robots: { index: false },
};

async function fetchOrder(id: string, token: string) {
  const backendUrl = process.env.BACKEND_URL;
  if (!backendUrl) return null;

  const res = await fetch(`${backendUrl}/api/v1/orders/${id}`, {
    headers: { Authorization: `Bearer ${token}` },
    cache: "no-store",
  });

  if (!res.ok) return null;
  return res.json();
}

export default async function OrderPage({
  params,
}: {
  params: Promise<{ id: string }>;
}) {
  const { id } = await params;

  const cookieStore = await cookies();
  const token = cookieStore.get("access_token")?.value;
  if (!token) redirect("/auth/error?reason=unauthorized");

  const order = await fetchOrder(id, token);
  if (!order) notFound();

  return (
    <>
      <nav className="bg-gray-50 border-b border-gray-100">
        <div className="max-w-2xl mx-auto px-4 py-3 flex items-center gap-1 text-sm text-gray-500">
          <Link href="/" className="hover:text-gray-900 transition-colors">Главная</Link>
          <ChevronRight className="h-3.5 w-3.5 text-gray-300 shrink-0" />
          <Link href="/dashboard" className="hover:text-gray-900 transition-colors">Мои заказы</Link>
          <ChevronRight className="h-3.5 w-3.5 text-gray-300 shrink-0" />
          <span className="text-gray-900 font-medium">Заказ № {id.slice(0, 8).toUpperCase()}</span>
        </div>
      </nav>
      <main className="min-h-screen bg-gray-50 py-10 px-4">
        <div className="max-w-lg mx-auto">
          <OrderStatus orderId={id} initialOrder={order} />
        </div>
      </main>
    </>
  );
}
