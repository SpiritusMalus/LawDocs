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

// Меняет адрес уведомлений заказа без пересылки письма (форму не перезаполняем).
export function changeOrderEmail(orderId: string, email: string): Promise<Response> {
  return fetch(`/api/orders/${orderId}/email`, {
    method: "PATCH",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ email }),
  });
}

// Пересылает письмо по заказу; опциональный email сперва меняет адрес уведомлений.
export function resendNotification(orderId: string, email?: string): Promise<Response> {
  return fetch(`/api/orders/${orderId}/resend`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(email ? { email } : {}),
  });
}
