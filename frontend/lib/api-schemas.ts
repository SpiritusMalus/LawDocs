// API Response Types - validated at runtime
export type OrderInitResponse = {
  order_id: string;
  requires_verification: boolean;
  redirect_to: string | null;
};

export type VerifyMagicLinkResponse = {
  access_token: string;
  user: {
    id: string;
    email: string;
  };
  order_id?: string;
};

export type OrderStatus = "draft" | "pending_payment" | "paid" | "generating" | "done" | "failed" | "refunded";

export type OrdersList = Array<{
  id: string;
  situation_id: string;
  status: OrderStatus;
  amount: number;
  created_at: string;
  has_document: boolean;
}>;

export type OrderDetail = {
  id: string;
  situation_id: string;
  status: OrderStatus;
  amount: number;
  created_at: string;
  paid_at: string | null;
};

// Runtime validators
function isValidUUID(value: unknown): value is string {
  if (typeof value !== "string") return false;
  return /^[0-9a-f]{8}-[0-9a-f]{4}-4[0-9a-f]{3}-[89ab][0-9a-f]{3}-[0-9a-f]{12}$/i.test(value);
}

function isValidEmail(value: unknown): value is string {
  if (typeof value !== "string") return false;
  return value.length > 0 && value.length <= 254 && value.includes("@");
}

export function validateOrderInitResponse(data: unknown): OrderInitResponse {
  if (typeof data !== "object" || data === null) {
    throw new Error("Invalid response format");
  }
  const obj = data as Record<string, unknown>;
  if (!isValidUUID(obj.order_id)) {
    throw new Error("Invalid order_id format");
  }
  return {
    order_id: obj.order_id,
    requires_verification: obj.requires_verification !== false,
    redirect_to: typeof obj.redirect_to === "string" ? obj.redirect_to : null,
  };
}

export function validateVerifyMagicLinkResponse(data: unknown): VerifyMagicLinkResponse {
  if (typeof data !== "object" || data === null) {
    throw new Error("Invalid response format");
  }
  const obj = data as Record<string, unknown>;
  if (typeof obj.access_token !== "string" || obj.access_token.length === 0) {
    throw new Error("Invalid access_token");
  }
  if (typeof obj.user !== "object" || obj.user === null) {
    throw new Error("Invalid user object");
  }
  const user = obj.user as Record<string, unknown>;
  if (!isValidUUID(user.id)) {
    throw new Error("Invalid user.id format");
  }
  if (!isValidEmail(user.email)) {
    throw new Error("Invalid user.email format");
  }
  return {
    access_token: obj.access_token,
    user: { id: user.id, email: user.email },
    order_id: isValidUUID(obj.order_id) ? (obj.order_id as string) : undefined,
  };
}
