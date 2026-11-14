# Tezyubor — arxitektura va audit bazasi

Ushbu hujjat `main` branchdagi joriy kodga asoslanadi. `work/phase-4-production` alohida ishchi branch; undagi o‘zgarishlar alohida qayd etiladi.

## Tuzilma

- `mobile/` — Flutter, Riverpod va `go_router`; ekranlar `lib/features/` ichida.
- `backend/` — FastAPI modulli monolit. Hozircha `app/modules/auth/` moduli mavjud.
- `admin/` — kelajakdagi React/TypeScript paneli; hozircha amalga oshirilmagan.

## Hozirgi backend

- Auth qatlami HTTP router → service → store tartibida. PostgreSQL saqlash qatlami `psycopg` va connection pool ishlatadi; ORM yo‘q.
- `DATABASE_URL` berilganda `users`, `refresh_tokens` va `sms_requests` jadvallari ishlatiladi.
- `DATABASE_URL` hozir ixtiyoriy. Production’da u bo‘lmasa ilova ogohlantirish yozib, ma’lumotni RAM’da saqlaydi; qayta ishga tushganda foydalanuvchi, PIN va sessiya yo‘qoladi.
- Sxema server ishga tushganda `CREATE TABLE IF NOT EXISTS` bilan yaratiladi. Alembic yoki versiyalangan migratsiyalar yo‘q.
- OTP challenge va `AuditLog` RAM’da turadi, bir nechta process yoki instance o‘rtasida bo‘lishilmaydi.
- Redis, wallet/account/card/transaction backend va balans ledger’i yo‘q. Haqiqiy bank yoki to‘lov provayderiga ulanish yo‘q.

## Auth va xavfsizlikning hozirgi holati

- OTP kodi HMAC bilan saqlanadi; muddati va urinishlar soni tekshiriladi. `APP_ENV != production` bo‘lsa test kodi ishlatiladi va SMS yuborilmaydi.
- Access JWT HS256 va 10 daqiqalik muddatga ega. Refresh tokenning faqat SHA-256 xeshi PostgreSQL’da saqlanadi; token aylantiriladi va qayta ishlatilishi aniqlanadi.
- PIN `scrypt` bilan xeshlanadi; ketma-ket noto‘g‘ri urinishlar cheklanadi.
- Hozirgi service audit hodisalariga maxfiy qiymatlarni kiritmaydi, lekin log RAM’da saqlanadi va append-only DB kafolati yo‘q.
- Logout faqat qurilmadagi secure storage’ni tozalaydi; server tomonda tokenni bekor qilish endpointi yo‘q.
- Umumiy API rate limiting, CORS sozlamasi va Redis ishlamay qolgandagi siyosat yo‘q.

## Hozirgi mobile

- `API_MODE=real` faqat auth endpointlaridan foydalanadi. Wallet doim `MockWalletRepository` orqali ishlaydi; TEST banneri va chek soxta to‘lovni haqiqiy deb ko‘rsatmaydi.
- Access/refresh token va maskalangan telefon `flutter_secure_storage`da saqlanadi.
- `local_auth` biometric paketi yo‘q. `mobile/android/` va `mobile/ios/` platforma loyihalari Git’da yo‘q; APK workflow Android scaffold’ini vaqtincha yaratadi.
- Chek hozir matn ko‘rinishida; PDF eksporti yo‘q.

## CI va release’ning hozirgi holati

- Backend CI PostgreSQL service’ini ishga tushirib unittest to‘plamini bajaradi; Redis integration testlari yo‘q.
- `main` branchdagi APK workflow Flutter analyze/test xatolarini e’tiborsiz qoldirishi mumkin edi va pull request triggeriga ega emas edi.
- APK workflow Android scaffold yaratadi. Release signing, qurilmaga o‘rnatib tekshirish va iOS build hozircha tasdiqlanmagan.
- Phase 4 branchida CI o‘zgarishlari kiritildi; ularning GitHub Actions natijasi alohida tekshiriladi.

## Phase 4 uchun moliyaviy xavfsizlik chegarasi

- Bank yoki to‘lov provayderining rasmiy API hujjati va tegishli kelishuv bo‘lmasa, tashqi pul o‘tkazmasi ulanmaydi.
- Mock wallet va mock transfer TEST sifatida aniq belgilanadi; production pul oqimi deb ko‘rsatilmaydi.
- Moliyaviy balansning yagona ishonchli manbai PostgreSQL bo‘ladi; Redis balansning yagona manbai bo‘lmaydi.
- Ledger qo‘shilganda barcha summalar integer tiyinlarda saqlanadi; transaction va double-entry yozuvlari bitta ACID tranzaksiyada bajariladi.
- PAN/CVV saqlanmaydi; faqat tasdiqlangan provayder tokenidan foydalanish imkoniyati keyingi integratsiya bosqichida baholanadi.
