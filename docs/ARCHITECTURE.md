# Tezyubor — arxitektura (qisqa)

## Tarkib
- `mobile/` — Flutter. `lib/core` (tema, router, brend), `lib/features/<modul>`, `lib/shared`.
- `backend/` — FastAPI modulli monolit: `app/modules/<modul>` (auth, keyin user, card, payment, transfer, transaction, cashback, notification, audit, admin).
- `admin/` — React + TS (keyin).

## Qatlamlar (backend)
`router.py` (HTTP) → `service.py` (biznes mantiq) → `stores.py` (Protocol). Xotira implementatsiyasi hozir;
Redis/PostgreSQL implementatsiyasi shu Protocol'lar orqali almashtiriladi, service o'zgarmaydi.

## Auth modeli (1-bosqich, bajarilgan)
- OTP: 6 xona, 120 s, 5 urinish, 60 s cooldown, soatiga 5 so'rov; HMAC bilan xeshlanadi, bir martalik.
- Access JWT 10 daqiqa (HS256, algoritm qat'iy); refresh token aylantiriladi, bazada faqat SHA-256 xesh;
  qayta ishlatilsa butun oila bekor qilinadi.
- PIN: scrypt; 5 xato → 15 daqiqa blok. 4 xonali PIN offline buzishga kuchsiz, shuning uchun himoya serverda.
- Audit: otp_requested/otp_failed/login_*/pin_*/refresh_reuse_detected. Maxfiy qiymatlar yozilmaydi, telefon maskalanadi.
- Test rejimi (`APP_ENV != production`): OTP doim 123456, SMS yuborilmaydi. Production'da haqiqiy SMS sender bo'lmasa ilova ishga tushmaydi.

## Pul operatsiyalari (keyingi bosqichlar, majburiy)
Idempotency-Key, tranzaksiya holatlari (created→pending→succeeded/failed/reversed), double-entry yozuvlar,
server tomonida summa/komissiya qayta hisoblash, provayder bilan reconciliation, append-only audit.
Karta: faqat provayder tokeni, PAN/CVV serverda saqlanmaydi.
