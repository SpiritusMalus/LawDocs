'use server';

import { cookies } from 'next/headers';

export async function logoutAction() {
  const cookieStore = await cookies();
  cookieStore.delete('access_token');
  return { success: true };
}
