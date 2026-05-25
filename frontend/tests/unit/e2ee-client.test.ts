import { describe, it, expect, beforeEach } from "vitest";
import nacl from "tweetnacl";
import { encodeBase64, decodeBase64, encodeUTF8 } from "tweetnacl-util";
import { E2EEClient } from "@/lib/e2ee-client";

// nacl box: nonce[24] | ephemeralPub[32] | box(data)[data.length+16]
const NONCE_LEN = nacl.box.nonceLength;   // 24
const PUB_LEN   = nacl.box.publicKeyLength; // 32
const AES_NONCE_LEN = 12;
const AES_KEY_LEN   = 32;

function concat(...chunks: Uint8Array[]): Uint8Array {
  const total = chunks.reduce((s, c) => s + c.length, 0);
  const out = new Uint8Array(total);
  let off = 0;
  for (const c of chunks) { out.set(c, off); off += c.length; }
  return out;
}

describe("E2EEClient", () => {
  describe("generateKeyPair", () => {
    it("returns base64 publicKey and privateKey", () => {
      const kp = E2EEClient.generateKeyPair();
      expect(kp.publicKey).toBeTruthy();
      expect(kp.privateKey).toBeTruthy();
      expect(decodeBase64(kp.publicKey).length).toBe(32);
      expect(decodeBase64(kp.privateKey).length).toBe(32);
    });

    it("generates unique key pairs each call", () => {
      const a = E2EEClient.generateKeyPair();
      const b = E2EEClient.generateKeyPair();
      expect(a.publicKey).not.toBe(b.publicKey);
      expect(a.privateKey).not.toBe(b.privateKey);
    });
  });

  describe("localStorage helpers", () => {
    beforeEach(() => {
      localStorage.clear();
    });

    it("saves and retrieves private key", () => {
      const kp = E2EEClient.generateKeyPair();
      E2EEClient.savePrivateKeyToLocalStorage(kp.privateKey);
      expect(E2EEClient.getPrivateKeyFromLocalStorage()).toBe(kp.privateKey);
    });

    it("saves and retrieves public key", () => {
      const kp = E2EEClient.generateKeyPair();
      E2EEClient.savePublicKeyToLocalStorage(kp.publicKey);
      expect(E2EEClient.getPublicKeyFromLocalStorage()).toBe(kp.publicKey);
    });

    it("hasKeys() returns false when no keys stored", () => {
      expect(E2EEClient.hasKeys()).toBe(false);
    });

    it("hasKeys() returns true only when both keys stored", () => {
      const kp = E2EEClient.generateKeyPair();
      E2EEClient.savePrivateKeyToLocalStorage(kp.privateKey);
      expect(E2EEClient.hasKeys()).toBe(false);
      E2EEClient.savePublicKeyToLocalStorage(kp.publicKey);
      expect(E2EEClient.hasKeys()).toBe(true);
    });
  });

  describe("encryptFormData / decryptFormData", () => {
    it("round-trips an object", () => {
      const kp = E2EEClient.generateKeyPair();
      const data = { name: "Иван", amount: 5000, nested: { foo: true } };
      const encrypted = E2EEClient.encryptFormData(data, kp.publicKey);
      const decrypted = E2EEClient.decryptFormData<typeof data>(encrypted, kp.privateKey);
      expect(decrypted).toEqual(data);
    });

    it("throws on wrong private key", () => {
      const kp = E2EEClient.generateKeyPair();
      const wrong = E2EEClient.generateKeyPair();
      const encrypted = E2EEClient.encryptFormData({ x: 1 }, kp.publicKey);
      expect(() => E2EEClient.decryptFormData(encrypted, wrong.privateKey)).toThrow();
    });
  });

  describe("createPasswordProtectedBackup / decryptPasswordProtectedBackup", () => {
    it("round-trips private key with correct password", async () => {
      const kp = E2EEClient.generateKeyPair();
      const password = "correct-horse-battery-staple";
      const backup = await E2EEClient.createPasswordProtectedBackup(kp.privateKey, password);
      const recovered = await E2EEClient.decryptPasswordProtectedBackup(backup, password);
      expect(recovered).toBe(kp.privateKey);
    });

    it("throws on wrong password", async () => {
      const kp = E2EEClient.generateKeyPair();
      const backup = await E2EEClient.createPasswordProtectedBackup(kp.privateKey, "right");
      await expect(
        E2EEClient.decryptPasswordProtectedBackup(backup, "wrong")
      ).rejects.toThrow();
    });
  });

  describe("decryptFile", () => {
    it("decrypts a file blob produced by the backend format", async () => {
      // Simulate backend: e2ee_file.py builds key_blob[104] | aes_nonce[12] | aes_ct
      const recipientKP = nacl.box.keyPair();
      const aesKeyRaw = nacl.randomBytes(AES_KEY_LEN);
      const ephemeral = nacl.box.keyPair();
      const naclNonce = nacl.randomBytes(NONCE_LEN);

      // nacl.box(aesKey[32]) → 32+16=48 bytes
      const boxed = nacl.box(aesKeyRaw, naclNonce, recipientKP.publicKey, ephemeral.secretKey);
      const keyBlob = concat(naclNonce, ephemeral.publicKey, boxed); // 24+32+48=104

      const cryptoKey = await crypto.subtle.importKey(
        "raw", aesKeyRaw, "AES-GCM", false, ["encrypt"]
      );
      const aesNonce = crypto.getRandomValues(new Uint8Array(AES_NONCE_LEN));
      const plaintext = encodeUTF8("test file content");
      const aesCt = new Uint8Array(await crypto.subtle.encrypt(
        { name: "AES-GCM", iv: aesNonce }, cryptoKey, plaintext
      ));

      const encrypted = concat(keyBlob, aesNonce, aesCt);
      const privateKeyB64 = encodeBase64(recipientKP.secretKey);

      const result = await E2EEClient.decryptFile(encrypted, privateKeyB64);
      expect(new Uint8Array(result)).toEqual(plaintext);
    });

    it("throws on wrong private key", async () => {
      const recipientKP = nacl.box.keyPair();
      const wrongKP = nacl.box.keyPair();
      const aesKeyRaw = nacl.randomBytes(AES_KEY_LEN);
      const ephemeral = nacl.box.keyPair();
      const naclNonce = nacl.randomBytes(NONCE_LEN);
      const boxed = nacl.box(aesKeyRaw, naclNonce, recipientKP.publicKey, ephemeral.secretKey);
      const keyBlob = concat(naclNonce, ephemeral.publicKey, boxed);

      const cryptoKey = await crypto.subtle.importKey(
        "raw", aesKeyRaw, "AES-GCM", false, ["encrypt"]
      );
      const aesNonce = crypto.getRandomValues(new Uint8Array(AES_NONCE_LEN));
      const aesCt = new Uint8Array(await crypto.subtle.encrypt(
        { name: "AES-GCM", iv: aesNonce }, cryptoKey, encodeUTF8("data")
      ));

      const encrypted = concat(keyBlob, aesNonce, aesCt);
      await expect(
        E2EEClient.decryptFile(encrypted, encodeBase64(wrongKP.secretKey))
      ).rejects.toThrow();
    });
  });
});
