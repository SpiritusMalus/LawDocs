'use server';

import { cookies } from 'next/headers';

export async function adminLoginAction(secret: string): Promise<{ success: boolean; error?: string }> {
  if (!secret) {
    return { success: false, error: 'Secret is required' };
  }

  try {
    const tokenRes = await fetch(`${process.env.BACKEND_URL}/api/v1/reviews/admin/token`, {
      method: 'POST',
      headers: { 'X-Admin-Secret': secret },
    });

    if (!tokenRes.ok) {
      return { success: false, error: 'Invalid password' };
    }

    const { admin_token } = await tokenRes.json();
    const cookieStore = await cookies();
    cookieStore.set('admin_token', admin_token, {
      httpOnly: true,
      secure: process.env.NODE_ENV === 'production',
      sameSite: 'strict',
      path: '/',
      maxAge: 14400,
    });

    return { success: true };
  } catch (err) {
    return { success: false, error: 'Login failed' };
  }
}

export async function adminLogoutAction(): Promise<void> {
  const cookieStore = await cookies();
  cookieStore.set('admin_token', '', { maxAge: 0, path: '/' });
}
