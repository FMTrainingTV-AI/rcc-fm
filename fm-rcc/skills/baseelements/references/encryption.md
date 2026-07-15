# BE Encryption / Hashing / Signatures recipes

Native FileMaker has `CryptEncrypt`/`CryptDigest`/`CryptGenerateSignature` (FM 16+). Prefer those
when they fit. Reach for BE when you need a specific cipher + IV for **interoperability with non-FM
systems**, RSA public/private-key workflows, or BE's AES format.

## Hashing — `BE_MessageDigest`

```
Set Variable [ $hash ; BE_MessageDigest ( $text ) ]                                  // default MD5
Set Variable [ $hash ; BE_MessageDigest ( $text ; BE_MessageDigestAlgorithmSHA256 ; BE_EncodingHex ) ]
Set Variable [ $hash ; BE_MessageDigest ( $text ; 2 ; 2 ) ]                          // 2 = SHA256, 2 = Base64
```

- Algorithm constant: `BE_MessageDigestAlgorithmMD5` (1), `BE_MessageDigestAlgorithmSHA256` (2), other
  SHA variants — fetch `Functions/Constants.md` for the full list and exact spelling (older docs use
  `BE_MessageDigestType*` names; the numeric values are stable).
- Encoding constant: `BE_EncodingHex` (1), `BE_EncodingBase64` (2).
- ⚠️ If a constant *name* is wrong or undefined on the installed build, FileMaker evaluates it to **empty**
  (no error) — so the call silently falls back to defaults (MD5 / hex). If unsure of the exact constant
  name, use the **numeric value** (e.g. `2` for SHA256, `2` for Base64) which is stable across versions.

**HMAC:** the old `BE_HMAC` function is **deprecated/removed** — don't use it. For an HMAC signature,
use native FileMaker `CryptAuthCode` (FM 18+), which is purpose-built for HMAC (e.g.
`CryptAuthCode ( data ; "SHA256" ; key )`).

## AES (BE format) — `BE_Encrypt_AES` / `BE_Decrypt_AES`

```
Set Variable [ $cipher ; BE_Encrypt_AES ( $key ; $plainText ) ]
Set Variable [ $err    ; BE_GetLastError ]
Set Variable [ $plain  ; BE_Decrypt_AES ( $key ; $cipher ) ]
```

⚠️ This is BE's **own** AES format — decryptable by the BE plugin, not guaranteed to interoperate with
other AES tools. For round-trips with outside systems, use `BE_CipherEncrypt` (below) with an explicit
named cipher + IV.

## Named cipher + IV (interoperable) — `BE_CipherEncrypt` / `BE_CipherDecrypt`

```
# aes-256-cbc with hex-encoded data, key, and IV
Set Variable [ $enc ; BE_CipherEncrypt (
    "aes-256-cbc" ;
    HexEncode ( $plainText ) ;
    "603deb1015ca71be2b73aef0857d77811f352c073b6108d72d9810a30914dff4" ;   // 32-byte key as hex
    "000102030405060708090a0b0c0d0e0f"                                      // 16-byte IV as hex
) ]
Set Variable [ $dec ; BE_CipherDecrypt ( "aes-256-cbc" ; $enc ; $key ; $iv ) ]
```

Signature: `( cipher ; data ; key ; iv ; { paddingBoolean ; fileNameWithExtension } )`.
- `cipher` is an OpenSSL cipher name string (`aes-256-cbc`, `aes-128-cbc`, …).
- Match the key/IV length to the cipher; mismatches surface in `BE_GetLastError`.
- Use this (not `BE_Encrypt_AES`) when another system must encrypt/decrypt the same data.

## RSA public/private key — keypair, encrypt, sign, verify

```
# generate a keypair
Set Variable [ $privateKey ; BE_CreateKeyPair ]
Set Variable [ $publicKey  ; BE_GetPublicKey ( $privateKey ) ]

# asymmetric encrypt/decrypt
Set Variable [ $enc ; BE_EncryptWithKey ( $plainText ; $publicKey ) ]
Set Variable [ $dec ; BE_DecryptWithKey ( $enc ; $privateKey ) ]

# digital signatures
Set Variable [ $sig ; BE_SignatureGenerateRSA ( $data ; $privateKey ) ]
Set Variable [ $ok  ; BE_SignatureVerifyRSA ( $data ; $publicKey ; $sig ) ]   // True if valid
```

- `BE_SignatureGenerateRSA ( data ; privateKey ; { password ; algorithm ; fileName } )` — optional
  private-key password and signature algorithm.
- `BE_SignatureVerifyRSA ( data ; publicKey ; { signature ; algorithm } )` — returns validity.

## Notes

- **Check `BE_GetLastError` after every crypto call** — wrong key length, bad IV, malformed key, or
  padding errors return `?`/empty and the real reason is in the error code.
- Store keys/secrets outside the calc (a settings table, container, or env), never inline in a script
  that ships.
- Encodings: pair these with `HexEncode`/`HexDecode` and `Base64Encode`/`Base64Decode` (native FM) when
  moving binary through text.
- Fetch a function's doc for exact params:
  `curl -sL https://raw.githubusercontent.com/GoyaPtyLtd/BaseElements-Plugin/main/docs/Functions/BE_CipherEncrypt.md`
