/**
 * In-memory rate limiter. Sufficient for a single-instance Phase 1 deploy
 * (Vercel preview, single VPS). When we go multi-instance, swap for KV/Redis.
 */

interface Bucket {
  count: number;
  resetAt: number;
}

const BUCKETS = new Map<string, Bucket>();

interface RateLimitOptions {
  /** Window length in milliseconds. */
  windowMs: number;
  /** Max requests allowed per key in the window. */
  max: number;
}

export interface RateLimitResult {
  ok: boolean;
  remaining: number;
  retryAfterMs: number;
}

export function rateLimit(key: string, opts: RateLimitOptions): RateLimitResult {
  const now = Date.now();
  const existing = BUCKETS.get(key);

  if (!existing || existing.resetAt <= now) {
    const fresh: Bucket = { count: 1, resetAt: now + opts.windowMs };
    BUCKETS.set(key, fresh);
    return { ok: true, remaining: opts.max - 1, retryAfterMs: 0 };
  }

  if (existing.count >= opts.max) {
    return { ok: false, remaining: 0, retryAfterMs: existing.resetAt - now };
  }

  existing.count += 1;
  return {
    ok: true,
    remaining: opts.max - existing.count,
    retryAfterMs: 0,
  };
}

/**
 * Periodically prunes expired buckets so the Map doesn't grow unbounded.
 * Cheap because we only walk entries when called.
 */
export function pruneRateLimitBuckets(): void {
  const now = Date.now();
  for (const [key, bucket] of BUCKETS) {
    if (bucket.resetAt <= now) BUCKETS.delete(key);
  }
}
