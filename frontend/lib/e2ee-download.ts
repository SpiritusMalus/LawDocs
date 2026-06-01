// Скачивание документа заказа. Для зашифрованных файлов расшифровывает
// приватным ключом из localStorage. Вынесено из order-status.tsx без изменения
// поведения (Фаза 4 рефакторинга).
import { E2EEClient } from "@/lib/e2ee-client";
import { ymGoal } from "@/lib/analytics";

/** Приватного ключа нет в этом браузере — нужно восстановить доступ.
 * Отдельный тип, чтобы UI показал форму восстановления, а не просто текст. */
export class MissingKeyError extends Error {
  constructor() {
    super("Ключ доступа не найден в этом браузере.");
    this.name = "MissingKeyError";
  }
}

export async function downloadDocument(
  orderId: string,
  fmt: "docx" | "pdf",
  situationId: string,
): Promise<void> {
  const res = await fetch(`/api/documents/${orderId}/download-info/${fmt}`);
  if (!res.ok) throw new Error("Не удалось получить ссылку на файл");

  const { url, is_encrypted, filename } = (await res.json()) as {
    url: string;
    is_encrypted: boolean;
    filename: string;
  };

  ymGoal("document_downloaded", { format: fmt, situation: situationId });

  if (!is_encrypted) {
    // Старые заказы без шифрования — открываем напрямую
    const a = document.createElement("a");
    a.href = url;
    a.download = filename;
    a.click();
    return;
  }

  const privateKey = E2EEClient.getPrivateKeyFromLocalStorage();
  if (!privateKey) {
    throw new MissingKeyError();
  }

  const encryptedRes = await fetch(url);
  if (!encryptedRes.ok) throw new Error("Ошибка при скачивании файла");

  const encryptedBytes = new Uint8Array(await encryptedRes.arrayBuffer());
  const plaintext = await E2EEClient.decryptFile(encryptedBytes, privateKey);

  const blob = new Blob([plaintext], {
    type:
      fmt === "pdf"
        ? "application/pdf"
        : "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
  });
  const blobUrl = URL.createObjectURL(blob);
  const a = document.createElement("a");
  a.href = blobUrl;
  a.download = filename;
  a.click();
  setTimeout(() => URL.revokeObjectURL(blobUrl), 10_000);
}
