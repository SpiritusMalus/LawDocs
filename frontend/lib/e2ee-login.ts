// Логин по ключу (challenge-response). Приватный ключ НЕ уходит на сервер:
// сервер шлёт зашифрованный nonce, браузер расшифровывает его приватным ключом
// и возвращает — это доказывает владение. Публичный ключ = идентификатор аккаунта.
import { E2EEClient } from "@/lib/e2ee-client";

/**
 * Логинит по приватному ключу. Возвращает путь для редиректа (кабинет).
 * Бросает Error с человекочитаемым текстом при любой проблеме.
 */
export async function loginViaPrivateKey(privateKeyB64: string): Promise<string> {
  let publicKey: string;
  try {
    publicKey = E2EEClient.publicKeyFromPrivateKey(privateKeyB64.trim());
  } catch {
    throw new Error("Неверный формат ключа");
  }

  const chRes = await fetch("/api/auth/key-challenge", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ public_key: publicKey }),
  });
  if (!chRes.ok) throw new Error("Не удалось начать вход. Попробуйте позже.");
  const { challenge_id, encrypted_challenge } = (await chRes.json()) as {
    challenge_id: string;
    encrypted_challenge: string;
  };

  const nonce = E2EEClient.solveChallenge(encrypted_challenge, privateKeyB64.trim());

  const loginRes = await fetch("/api/auth/key-login", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ challenge_id, nonce }),
  });
  if (loginRes.status === 401) {
    throw new Error("Под этим ключом нет документов. Проверьте, что выбрали верный ключ-файл.");
  }
  if (!loginRes.ok) throw new Error("Не удалось войти. Попробуйте позже.");

  const { redirectTo } = (await loginRes.json()) as { redirectTo: string };

  // Кладём ключ локально — он нужен для расшифровки документов в кабинете.
  E2EEClient.savePrivateKeyToLocalStorage(privateKeyB64.trim());
  E2EEClient.savePublicKeyToLocalStorage(publicKey);

  return redirectTo;
}

/** Логин из ключ-файла lawdocs-key.json. */
export async function loginViaKeyFile(file: File): Promise<string> {
  let keyData: { privateKey?: string; publicKey?: string };
  try {
    keyData = JSON.parse(await file.text());
  } catch {
    throw new Error("Неверный формат файла. Это должен быть lawdocs-key.json");
  }
  if (!keyData.privateKey) throw new Error("Файл не содержит приватный ключ");
  if (keyData.publicKey && !E2EEClient.keyPairMatches(keyData.privateKey, keyData.publicKey)) {
    throw new Error("Ключ-файл повреждён: ключи не соответствуют друг другу");
  }
  return loginViaPrivateKey(keyData.privateKey);
}
