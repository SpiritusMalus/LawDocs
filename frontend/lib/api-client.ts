// Тонкий клиент для эндпоинтов заказа. Инкапсулирует URL/метод/кэш,
// но возвращает сырой Response — обработку (res.ok, data.error) оставляем
// вызывающему, чтобы не менять поведение при выносе из order-status.tsx.

export function fetchOrder(orderId: string): Promise<Response> {
  return fetch(`/api/orders/${orderId}`, { cache: "no-store" });
}

export function retryOrder(orderId: string): Promise<Response> {
  return fetch(`/api/orders/${orderId}/retry`, { method: "POST" });
}

export function payOrder(orderId: string): Promise<Response> {
  return fetch(`/api/orders/${orderId}/pay`, { method: "POST" });
}
