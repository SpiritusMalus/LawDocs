// Восстановление E2EE-доступа из ключ-файла или фразы восстановления.
// Общая логика для страницы /recovery и инлайн-формы на странице заказа —
// крипта живёт в одном месте, не дублируется.
import { E2EEClient } from "@/lib/e2ee-client";

/**
 * Восстанавливает доступ из ключ-файла (lawdocs-key.json).
 * Сверяет пару ключей и принадлежность аккаунту, затем кладёт ключ в localStorage.
 * Бросает Error с человекочитаемым текстом при любой проблеме.
 */
export async function recoverViaKeyFile(file: File): Promise<void> {
  let keyData: { privateKey?: string; publicKey?: string };
  try {
    keyData = JSON.parse(await file.text());
  } catch {
    throw new Error("Неверный формат файла. Это должен быть lawdocs-key.json");
  }

  if (!keyData.privateKey) throw new Error("Файл не содержит приватный ключ");
  if (!keyData.publicKey) throw new Error("Файл не содержит публичный ключ");

  // Приватный ключ должен соответствовать публичному из того же файла.
  if (!E2EEClient.keyPairMatches(keyData.privateKey, keyData.publicKey)) {
    throw new Error("Ключ-файл повреждён: ключи не соответствуют друг другу");
  }

  // Ключ-файл должен принадлежать текущему аккаунту: сверяем с публичным
  // ключом, который сервер хранит для вошедшего пользователя.
  const meRes = await fetch("/api/user/me");
  if (!meRes.ok) {
    throw new Error("Не удалось проверить ключ. Войдите в аккаунт и попробуйте снова.");
  }
  const userData = (await meRes.json()) as { public_key?: string };
  if (!userData.public_key) throw new Error("Для этого аккаунта не настроено шифрование");
  if (userData.public_key !== keyData.publicKey) {
    throw new Error("Этот ключ-файл от другого аккаунта");
  }

  E2EEClient.savePrivateKeyToLocalStorage(keyData.privateKey);
  E2EEClient.savePublicKeyToLocalStorage(keyData.publicKey);
}

/**
 * Восстанавливает доступ по email + фразе восстановления.
 * Запрашивает у сервера зашифрованный backup ключа и расшифровывает его фразой.
 * Бросает Error с человекочитаемым текстом при любой проблеме.
 */
export async function recoverViaPhrase(email: string, phrase: string): Promise<void> {
  const res = await fetch("/api/auth/recover-access", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ email: email.trim().toLowerCase() }),
  });

  if (res.status === 404) throw new Error("Пользователь с таким email не найден");
  if (res.status === 400) throw new Error("Для этого аккаунта нет сохранённого ключа восстановления");
  if (!res.ok) throw new Error("Ошибка сервера. Попробуйте позже.");

  const { backup_encrypted } = (await res.json()) as { backup_encrypted: string };
  const privateKey = await E2EEClient.decryptPasswordProtectedBackup(backup_encrypted, phrase);
  E2EEClient.savePrivateKeyToLocalStorage(privateKey);

  const meRes = await fetch("/api/user/me");
  if (!meRes.ok) throw new Error("Не удалось получить публичный ключ");
  const userData = (await meRes.json()) as { public_key?: string };
  if (!userData.public_key) {
    throw new Error("Восстановление не удалось: на сервере нет публичного ключа. Напишите в поддержку.");
  }
  E2EEClient.savePublicKeyToLocalStorage(userData.public_key);
}
