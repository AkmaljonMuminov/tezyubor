# ORVEX PAY (kod nomi: Tezyubor) — arxitektura (qisqa)

## Tarkib
- `mobile/` — Flutter. `lib/core` (tema, router, brend), `lib/features/<modul>`, `lib/shared`.
- `backend/` — FastAPI modulli monolit: `app/modules/<modul>` (auth, keyin user, card, payment, transfer, transaction, cashback, notification, audit, admin).
- `admin/` — React + TS (keyin).

## Qatlamlar (backend)
`router.py` (HTTP) → `service.py` (biznes mantiq) → `stores.py` (Protocol). Har Protocol'ning xotira va PostgreSQL
implementatsiyasi bor (`pg_stores.py`, `wallet/pg_store.py`) va bir xil shartnoma testlaridan o'tadi; `DATABASE_URL` bo'lsa PostgreSQL.
Sxema: asosiy jadvallar `db.SCHEMA`, qolgani versiyalangan `app/migrations.py` (`schema_migrations`), advisory lock ostida.

## Auth modeli (1-bosqich, bajarilgan)
- OTP: 6 xona, 120 s, 5 urinish, 60 s cooldown, soatiga 5 so'rov; HMAC bilan xeshlanadi, bir martalik.
- Access JWT 10 daqiqa (HS256, algoritm qat'iy); refresh token aylantiriladi, bazada faqat SHA-256 xesh;
  qayta ishlatilsa butun oila bekor qilinadi.
- PIN: scrypt; 5 xato → 15 daqiqa blok. 4 xonali PIN offline buzishga kuchsiz, shuning uchun himoya serverda.
- Audit: otp_requested/otp_failed/login_*/pin_*/refresh_reuse_detected/logout/session_revoked/transfer_*. Maxfiy qiymatlar (OTP, PIN, token, karta raqami) yozilmaydi, telefon maskalanadi. Xotirada oxirgi 5000 ta, PostgreSQL'da `audit_log` jadvaliga faqat qo'shiladi (yozish xatosi so'rovni buzmaydi).
- Test rejimi (`APP_ENV != production`): OTP doim 123456, SMS yuborilmaydi. Production'da haqiqiy SMS sender bo'lmasa ilova ishga tushmaydi.

## Auth qotirish (feature/anorbank-integration)
- **Sessiya = refresh oilasi** (`auth_sessions`: qurilma nomi, oxirgi foydalanish, bekor qilingan vaqt). Access JWT `sid` ga ega; `verify_access` va `rotate` sessiya faolligini tekshiradi, shuning uchun logout/uzish access tokenni ham darhol o'ldiradi.
- **PIN**: urinish AVVAL atomik sanaladi (`begin_pin_attempt`, PostgreSQL'da `FOR UPDATE`), keyin tekshiriladi — parallel so'rovlar limitni aylanib o'tolmaydi. Blok muddati 15 daq × 2^n (yuqori chegara 24 soat), to'g'ri PIN darajani nolga qaytaradi. Ixtiyoriy `PIN_PEPPER` (`scrypt2`), eski xesh to'g'ri PIN kiritilganda avtomatik yangilanadi.
- **OTP**: challenge bazada; urinish va bir martalik iste'mol atomik (`bump_attempts`, `consume`).
- Eski (migratsiyadan oldingi) refresh oilalari uchun migratsiya sessiya yozuvini to'ldiradi.

## Hamyon (SANDBOX, `app/modules/wallet`)
- PAN saqlanmaydi: `BIN6 + last4 + HMAC(CARD_INDEX_KEY, PAN)`; CVV olinmaydi. Karta qo'shish/qidirish umumiy limit ostida.
- Pul: butun tiyin. `cards.balance >= 0` bazada CHECK; har harakat `ledger_entries` ga yoziladi (balans = jurnal yig'indisi, testlarda tekshiriladi).
- O'tkazma: `pending → completed | failed | expired | cancelled`. Tasdiqlashda avval foydalanuvchi qatori, keyin kartalar id tartibida `FOR UPDATE` (deadlock'siz, foydalanuvchi bo'yicha kunlik limit ham poygasiz). Xato holatlari (`expired`, `failed`) tranzaksiya yopilib, keyin xato ko'tariladi.
- `Idempotency-Key` (foydalanuvchi, kalit) bo'yicha unique; bir xil kalit + boshqa tana = 409.
- Haqiqiy bank/protsessing YO'Q: barcha javoblarda `sandbox: true`, yangi kartaga sinov balans beriladi (o'chirib-qayta qo'shish bilan takror berilmaydi).

## Pul operatsiyalari (haqiqiy provayder uchun keyingi bosqichlar, majburiy)
Idempotency-Key, tranzaksiya holatlari (created→pending→succeeded/failed/reversed), double-entry yozuvlar,
server tomonida summa/komissiya qayta hisoblash, provayder bilan reconciliation, append-only audit.
Karta: faqat provayder tokeni, PAN/CVV serverda saqlanmaydi.
