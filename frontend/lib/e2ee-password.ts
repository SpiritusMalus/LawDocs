// Аккаунт под паролем — вторая дверь к тем же ключам. Пароль оборачивает
// приватные ключи в браузере (AES-GCM + PBKDF2); сервер хранит только обёртку и
// pbkdf2-хэш пароля для аутентификации. Приватные ключи на сервер не уходят.
import { E2EEClient } from "@/lib/e2ee-client";

interface KeyringEntry {
  public_key: string;
  wrapped_private_key: string;
  label: string | null;
}

/**
 * Ставит пароль аккаунта и сохраняет под ним текущий ключ устройства в keyring.
 * Требует, чтобы ключ был в этом браузере (localStorage). Бросает Error с текстом.
 */
export async function setAccountPassword(password: string): Promise<void> {
  const privateKey = E2EEClient.getPrivateKeyFromLocalStorage();
  const publicKey = E2EEClient.getPublicKeyFromLocalStorage();
  if (!privateKey || !publicKey) {
    throw new Error("В этом браузере нет ключа. Войдите по ключу-файлу и повторите.");
  }

  const wrapped = await E2EEClient.createPasswordProtectedBackup(privateKey, password);

  const res = await fetch("/api/auth/set-password", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({
      password,
      wrapped_keys: [{ public_key: publicKey, wrapped_private_key: wrapped, label: "primary" }],
    }),
  });
  if (res.status === 401) throw new Error("Сначала войдите в аккаунт.");
  if (!res.ok) throw new Error("Не удалось сохранить пароль. Попробуйте позже.");
}

/**
 * Импортирует ключ-файлы в keyring под паролем аккаунта (объединение ключей).
 * Каждый приватный ключ оборачивается паролем в браузере; на сервер уходят только
 * обёртки. Документы не переподписываются. Возвращает общее число ключей в keyring.
 */
export async function importKeysToKeyring(files: File[], password: string): Promise<number> {
  if (files.length === 0) throw new Error("Выберите хотя бы один ключ-файл");

  const wrappedKeys: { public_key: string; wrapped_private_key: string; label: string }[] = [];
  for (const file of files) {
    let keyData: { privateKey?: string; publicKey?: string };
    try {
      keyData = JSON.parse(await file.text());
    } catch {
      throw new Error(`${file.name}: неверный формат (ожидается lawdocs-key.json)`);
    }
    if (!keyData.privateKey || !keyData.publicKey) {
      throw new Error(`${file.name}: файл не содержит пару ключей`);
    }
    if (!E2EEClient.keyPairMatches(keyData.privateKey, keyData.publicKey)) {
      throw new Error(`${file.name}: ключи не соответствуют друг другу`);
    }
    const wrapped = await E2EEClient.createPasswordProtectedBackup(keyData.privateKey, password);
    wrappedKeys.push({
      public_key: keyData.publicKey,
      wrapped_private_key: wrapped,
      label: file.name,
    });
  }

  const res = await fetch("/api/auth/keyring/import", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ password, wrapped_keys: wrappedKeys }),
  });
  if (res.status === 401) throw new Error("Неверный пароль аккаунта");
  if (res.status === 400) throw new Error("Сначала установите пароль аккаунта");
  if (!res.ok) throw new Error("Не удалось импортировать ключи. Попробуйте позже.");

  const { total_keys } = (await res.json()) as { total_keys: number };
  return total_keys;
}

/**
 * Логин email+паролем. Раскрывает первый подходящий ключ из keyring паролем и
 * кладёт его в localStorage (для расшифровки в кабинете). Возвращает путь редиректа.
 */
export async function loginViaPassword(email: string, password: string): Promise<string> {
  const res = await fetch("/api/auth/password-login", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ email: email.trim().toLowerCase(), password }),
  });
  if (res.status === 401) throw new Error("Неверный email или пароль");
  if (!res.ok) throw new Error("Не удалось войти. Попробуйте позже.");

  const { redirectTo, keyring } = (await res.json()) as {
    redirectTo: string;
    keyring: KeyringEntry[];
  };

  // Раскрываем ключи паролем локально; первый валидный кладём как ключ устройства.
  for (const entry of keyring) {
    try {
      const privateKey = await E2EEClient.decryptPasswordProtectedBackup(
        entry.wrapped_private_key,
        password,
      );
      if (E2EEClient.keyPairMatches(privateKey, entry.public_key)) {
        E2EEClient.savePrivateKeyToLocalStorage(privateKey);
        E2EEClient.savePublicKeyToLocalStorage(entry.public_key);
        break;
      }
    } catch {
      // Битый/несовпадающий blob — пропускаем, пробуем следующий.
    }
  }

  return redirectTo;
}
