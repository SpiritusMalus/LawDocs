import nacl from "tweetnacl";
import {
  decodeBase64,
  encodeBase64,
  decodeUTF8,
  encodeUTF8,
} from "tweetnacl-util";

/**
 * E2EEClient — сквозное шифрование на стороне браузера.
 *
 * Модель (см. E2EE_CLAUDE_CODE_INSTRUCTIONS.md):
 *  - Пара ключей TweetNaCl (nacl.box) генерируется в браузере.
 *  - Public key уходит на сервер, private key живёт ТОЛЬКО в localStorage.
 *  - Форма шифруется публичным ключом перед отправкой; сервер хранит шифртекст
 *    и не способен его расшифровать.
 *  - Резервная копия private key защищается паролем восстановления (AES-GCM
 *    + PBKDF2) — её можно вернуть, не давая серверу доступ к ключу.
 *
 * Формат шифртекста формы: base64( nonce[24] | ephemeralPublicKey[32] | box ).
 */

const NONCE_LENGTH = nacl.box.nonceLength; // 24
const PUBLIC_KEY_LENGTH = nacl.box.publicKeyLength; // 32

const PRIVATE_KEY_STORAGE_KEY = "e2ee_private_key";
const PUBLIC_KEY_STORAGE_KEY = "e2ee_public_key";

// Параметры защиты резервной копии (PBKDF2 → AES-GCM-256).
const PBKDF2_ITERATIONS = 200_000;
const PBKDF2_SALT_LENGTH = 16;
const AES_IV_LENGTH = 12;

export interface E2EEKeyPair {
  publicKey: string; // base64
  privateKey: string; // base64
}

function concatBytes(...chunks: Uint8Array[]): Uint8Array {
  const total = chunks.reduce((sum, c) => sum + c.length, 0);
  const out = new Uint8Array(total);
  let offset = 0;
  for (const chunk of chunks) {
    out.set(chunk, offset);
    offset += chunk.length;
  }
  return out;
}

// WebCrypto ждёт BufferSource поверх ArrayBuffer. tweetnacl-util и .slice() дают
// Uint8Array<ArrayBufferLike> (TS 5.7+), что несовместимо — копируем в свежий буфер.
function asBuffer(u: Uint8Array): Uint8Array<ArrayBuffer> {
  return new Uint8Array(u);
}

export class E2EEClient {
  /** Генерирует пару ключей. privateKey НИКОГДА не уходит на сервер. */
  static generateKeyPair(): E2EEKeyPair {
    const pair = nacl.box.keyPair();
    return {
      publicKey: encodeBase64(pair.publicKey),
      privateKey: encodeBase64(pair.secretKey),
    };
  }

  static savePrivateKeyToLocalStorage(privateKeyB64: string): void {
    if (typeof window === "undefined") return;
    window.localStorage.setItem(PRIVATE_KEY_STORAGE_KEY, privateKeyB64);
  }

  static getPrivateKeyFromLocalStorage(): string | null {
    if (typeof window === "undefined") return null;
    return window.localStorage.getItem(PRIVATE_KEY_STORAGE_KEY);
  }

  static savePublicKeyToLocalStorage(publicKeyB64: string): void {
    if (typeof window === "undefined") return;
    window.localStorage.setItem(PUBLIC_KEY_STORAGE_KEY, publicKeyB64);
  }

  static getPublicKeyFromLocalStorage(): string | null {
    if (typeof window === "undefined") return null;
    return window.localStorage.getItem(PUBLIC_KEY_STORAGE_KEY);
  }

  static hasKeys(): boolean {
    return (
      this.getPrivateKeyFromLocalStorage() !== null &&
      this.getPublicKeyFromLocalStorage() !== null
    );
  }

  /**
   * Шифрует данные формы публичным ключом получателя.
   * Использует одноразовую (ephemeral) пару отправителя — анонимный box.
   */
  static encryptFormData(
    formData: Record<string, unknown>,
    publicKeyB64: string
  ): string {
    const message = decodeUTF8(JSON.stringify(formData));
    const recipientPublicKey = decodeBase64(publicKeyB64);
    const nonce = nacl.randomBytes(NONCE_LENGTH);
    const ephemeral = nacl.box.keyPair();

    const box = nacl.box(message, nonce, recipientPublicKey, ephemeral.secretKey);

    return encodeBase64(concatBytes(nonce, ephemeral.publicKey, box));
  }

  /** Расшифровывает форму приватным ключом из localStorage. */
  static decryptFormData<T = Record<string, unknown>>(
    encryptedB64: string,
    privateKeyB64: string
  ): T {
    const packed = decodeBase64(encryptedB64);
    const nonce = packed.slice(0, NONCE_LENGTH);
    const ephemeralPublicKey = packed.slice(
      NONCE_LENGTH,
      NONCE_LENGTH + PUBLIC_KEY_LENGTH
    );
    const box = packed.slice(NONCE_LENGTH + PUBLIC_KEY_LENGTH);
    const privateKey = decodeBase64(privateKeyB64);

    const decrypted = nacl.box.open(
      box,
      nonce,
      ephemeralPublicKey,
      privateKey
    );
    if (!decrypted) {
      throw new Error("E2EE: не удалось расшифровать (неверный ключ или данные)");
    }

    return JSON.parse(encodeUTF8(decrypted)) as T;
  }

  /**
   * Резервная копия private key, защищённая паролем восстановления.
   * AES-GCM-256, ключ выводится из пароля через PBKDF2 (SHA-256).
   * Формат: base64( salt[16] | iv[12] | ciphertext ).
   */
  static async createPasswordProtectedBackup(
    privateKeyB64: string,
    password: string
  ): Promise<string> {
    const salt = crypto.getRandomValues(new Uint8Array(PBKDF2_SALT_LENGTH));
    const iv = crypto.getRandomValues(new Uint8Array(AES_IV_LENGTH));
    const key = await deriveAesKey(password, salt);

    const ciphertext = new Uint8Array(
      await crypto.subtle.encrypt(
        { name: "AES-GCM", iv: asBuffer(iv) },
        key,
        asBuffer(decodeUTF8(privateKeyB64))
      )
    );

    return encodeBase64(concatBytes(salt, iv, ciphertext));
  }

  /** Восстанавливает private key из защищённой паролем резервной копии. */
  static async decryptPasswordProtectedBackup(
    backupB64: string,
    password: string
  ): Promise<string> {
    const packed = decodeBase64(backupB64);
    const salt = packed.slice(0, PBKDF2_SALT_LENGTH);
    const iv = packed.slice(PBKDF2_SALT_LENGTH, PBKDF2_SALT_LENGTH + AES_IV_LENGTH);
    const ciphertext = packed.slice(PBKDF2_SALT_LENGTH + AES_IV_LENGTH);
    const key = await deriveAesKey(password, salt);

    let plaintext: ArrayBuffer;
    try {
      plaintext = await crypto.subtle.decrypt(
        { name: "AES-GCM", iv: asBuffer(iv) },
        key,
        asBuffer(ciphertext)
      );
    } catch {
      throw new Error("E2EE: неверный пароль восстановления");
    }

    return encodeUTF8(new Uint8Array(plaintext));
  }
}

async function deriveAesKey(
  password: string,
  salt: Uint8Array
): Promise<CryptoKey> {
  const baseKey = await crypto.subtle.importKey(
    "raw",
    asBuffer(decodeUTF8(password)),
    "PBKDF2",
    false,
    ["deriveKey"]
  );
  return crypto.subtle.deriveKey(
    {
      name: "PBKDF2",
      salt: asBuffer(salt),
      iterations: PBKDF2_ITERATIONS,
      hash: "SHA-256",
    },
    baseKey,
    { name: "AES-GCM", length: 256 },
    false,
    ["encrypt", "decrypt"]
  );
}
