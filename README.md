# Tezyubor

Mobil to'lov ilovasi (Android/iOS). Texnologiyalar: Flutter, FastAPI, PostgreSQL, Redis, React (admin).

## Holat (yangilangan: 2026-11-14, branch `feature/anorbank-integration`)

| Qism | Holat |
|---|---|
| Grafikalar: premium kit (navy/royal/oltin, T logotip, 25 ikonka, bannerlar, launcher ikonka) | ✅ Asl kit `design/premium_kit`, ilova uchun tozalangani `mobile/assets` (SVG ichida matn/pattern/filtr yo'q — Flutter chizmaydi). Telefon ekranida ko'rinishi odam ko'zi bilan tekshirilmagan |
| Flutter: splash, telefon, OTP, PIN yaratish/kirish | ⚠️ Yozilgan, **ishga tushirib tekshirilmagan** |
| Flutter: bosh sahifa, kartalar, tarix, kartaga o'tkazma, to'lovlar (mobil/kommunal) | ⚠️ Yozilgan (**mock ma'lumot**), ishga tushirib tekshirilmagan |
| Flutter: pastki navigatsiya (Asosiy, O'tkazmalar, To'lov, Monitoring, Profil) | ⚠️ Yozilgan, ishga tushirib tekshirilmagan |
| Flutter: monitoring (oylik tushum/xarajat, filtr, kunlar bo'yicha), so'nggi qabul qiluvchilar, kartalar orasida o'tkazma | ⚠️ Yozilgan (mock), ishga tushirib tekshirilmagan |
| Flutter: profil (maskalangan telefon), balansni yashirish, chiqish | ⚠️ Yozilgan. Chiqish endi serverga ham `POST /v1/auth/logout` yuboradi (internet bo'lmasa qurilma baribir tozalanadi). Lokal commit, CI'da hali tekshirilmagan |
| Flutter: To'lov bo'limi — qidiruv, 20 kategoriya, tanlangan to'lovlar, mobil operatorlar (telefon qatori), kommunal variantlar, elektr uchun hudud + ETK tanlash, xizmat bo'yicha tarix | ⚠️ Yozilgan (mock). Operator/xizmat nomlari faqat ko'rsatish uchun, ular bilan haqiqiy integratsiya yo'q. ETK ro'yxati faqat Samarqand uchun test ma'lumoti, qolgan hududlarda "tez orada"; boshqa kategoriyalar "Tez orada" |
| Flutter: chek — to'lovdan keyin va tarixdan ochiladi, tafsilotlar (karta maskalangan), matnni nusxalash | ⚠️ Yozilgan. Test rejimida chekda "TEST CHEK — haqiqiy to'lov emas" yozuvi bor. PDF/rasm sifatida ulashish yo'q |
| Flutter: haqiqiy HTTP klient (`API_MODE=real`) — kirish (haqiqiy SMS kod); hamyon baribir TEST | ⚠️ Yozilgan, klient testlari soxta HTTP bilan. Haqiqiy backend + telefon bilan **birga sinalmagan** |
| Flutter testlar (`validators`, `wallet`, `http_auth`) | ⚠️ Yozilgan, ishga tushirilmagan (CI'da `flutter test` ishlaydi, natijasi build'ni to'xtatmaydi) |
| Backend auth yadrosi (OTP, tokenlar, PIN, audit) | ✅ **Qotirilgan** (AnorBank auditidan keyin): serverda logout va sessiyalar ro'yxati; access token sessiyaga bog'langan (bekor qilingan sessiya tokeni darhol o'tmaydi); PIN urinishlari parallel so'rovda ham aylantirib bo'lmaydi, blok har safar 2 baravar uzayadi (15 daq → 24 soat); ixtiyoriy `PIN_PEPPER`; OTP challenge va audit bazada. CI (PostgreSQL 16): 228 test o'tgan |
| Backend: SMS yuborish (Eskiz.uz) — token, qayta urinish, shablon, sutkalik limit, xatoda limitni qaytarish | ⚠️ Yozilgan, testlar (soxta HTTP bilan). **Haqiqiy Eskiz hisobi bilan jonli sinalmagan** — `python3 -m app.tools.sms_check <telefon>` bilan tekshiring |
| Backend HTTP qatlami (`router.py`, `main.py`): OTP → tasdiqlash → PIN → token aylanishi, xato formati, productionda `/docs` yopiq | ✅ CI'da haqiqiy FastAPI (`TestClient`) bilan sinalgan, SMS soxta yuboruvchi bilan |
| Backend: karta, o'tkazma, tarix, chek | ⚠️ **SANDBOX** bor (`WALLET_ENABLED=true` bilan yoqiladi, standart o'chiq): PAN saqlanmaydi, CVV olinmaydi, summa/komissiyani server hisoblaydi, `Idempotency-Key`, serverda PIN bilan tasdiq, atomik pul harakati + jurnal. CI'da PostgreSQL bilan sinalgan (parallel testlar ham). **Haqiqiy bank yo'q — barcha pul sinov qiymat.** To'lovlar (kommunal/mobil) backendda YO'Q. Mobil hamyon hali ulanmagan (mock) |
| Biometrika (mobil) | ⚠️ Yozilgan (`local_auth`, PIN zaxira bilan; faqat ilovani ochadi, pul harakati serverda PIN bilan). Testlar yozilgan, lekin CI'da hali yurmagan va haqiqiy qurilmada sinalmagan |
| O'tkazmada PIN tasdig'i | ✅ Backendda (sandbox); mobilga ulanmagan |
| PIN tiklash, OTP qayta yuborish | ❌ Boshlanmagan |
| Docker (`backend/Dockerfile`), Render (`render.yaml`) | ⚠️ CI'da image yig'iladi va `/health` tekshiriladi; **jonli deploy qilinmagan** |
| PostgreSQL | ✅ `DATABASE_URL` bilan: users, refresh_tokens, sms_requests, auth_sessions, otp_challenges, audit_log, cards, transfers, ledger_entries. Versiyalangan migratsiyalar (`schema_migrations`). CI'da PostgreSQL 16 bilan, restartdan keyin ma'lumot saqlanishi ham tekshirilgan. `DATABASE_URL` bo'lmasa — xotira (restartda yo'qoladi) |
| Redis, admin panel | ❌ Boshlanmagan |
| APK | ✅ GitHub Actions (`Build APK`), `.github/workflows/build-apk.yml` |

**Mock/test:** `API_MODE=mock` (standart) — OTP kodi `123456`, backendga ulanmaydi; balanslar, kartalar va tarix SOXTA (ilovada "TEST REJIMI" banneri bor).
`API_MODE=real` — kirish haqiqiy backend (`/v1/auth/*`) va haqiqiy SMS bilan; hamyon (kartalar, balans, to'lov, tarix) esa **baribir SOXTA** va ilovada "TEST HAMYON" banneri hamda "TEST CHEK" yozuvi turadi.
**Haqiqiy integratsiyalar yo'q:** SMS provayder, bank/protsessing, Uzcard/Humo, to'lov provayderlari — shartnoma va kalit kerak.

**Pul qoidalari (mobil):** summa tiynda `int` (double emas); har operatsiya uchun `Idempotency-Key` (kiritish o'zgarsa yangilanadi, qayta urinishda o'sha); komissiya/chegara serverda ham qayta tekshirilishi shart.

## Yangi API (backend)

| Endpoint | Vazifa |
|---|---|
| `POST /v1/auth/logout` | Refresh token egasining qurilma sessiyasini serverda bekor qiladi (noma'lum token ham 204 — taxmin qilib bo'lmaydi) |
| `GET /v1/auth/sessions`, `DELETE /v1/auth/sessions/{id}` | Faol qurilmalar ro'yxati; o'z sessiyasini uzish (boshqaning sessiyasi — 404) |
| `GET/POST /v1/wallet/cards`, `DELETE …/{id}`, `POST …/{id}/default` | Sandbox kartalar. Javobda faqat `masked_pan`, `last4`; to'liq PAN va CVV hech qayerda saqlanmaydi |
| `POST /v1/wallet/receiver/lookup` | Qabul qiluvchi kartasi: maskalangan ism (daqiqada 10 ta urinish limiti — raqamlarni taxmin qilishga qarshi) |
| `POST /v1/wallet/transfers` (`Idempotency-Key` majburiy) | O'tkazma taklifi: summa/komissiya/jami serverda hisoblanadi; 5 daqiqa ichida tasdiqlanadi |
| `POST /v1/wallet/transfers/{id}/confirm` `{pin}` | PIN serverda tekshiriladi (blok qoidalari bilan), pul bitta atomik tranzaksiyada o'tadi; takroriy chaqiriq qayta yechmaydi |
| `POST /v1/wallet/transfers/{id}/cancel`, `GET /v1/wallet/transactions[?limit&cursor&status&direction]`, `GET …/{id}` | Bekor qilish, tarix (kursor sahifalash), chek faqat tasdiqlangan o'tkazma uchun |

Hamyon javoblarida har doim `"sandbox": true`. Hamyon `.env` da `WALLET_ENABLED=true` va `CARD_INDEX_KEY` (>=32 belgi) bilan yoqiladi; komissiya/limit qiymatlari **o'rinbosar** (`TRANSFER_*`, `.env.example` ga qarang) — haqiqiy tarif biznes qarori.
`PIN_PEPPER` (ixtiyoriy, >=32 belgi) — bazaning o'zi sizib chiqsa ham 4 xonali PIN'ni taxmin qilib bo'lmasligi uchun; keyin yo'qotilsa shu kalit bilan yaratilgan PIN'lar tekshirilmaydi.

Batafsil audit va reja: [`docs/anorbank-analysis.md`](docs/anorbank-analysis.md).

## Backend

```bash
cd backend
python3 -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
cp ../.env.example ../.env     # JWT_SECRET va OTP_SECRET ni to'ldiring (kamida 32 belgi, har xil)
python3 -m unittest discover -s tests -t . -v        # yoki: pytest
export $(grep -v '^#' ../.env | xargs) && uvicorn app.main:create_app --factory --reload
```

### SMS (Eskiz)
`.env` da `SMS_PROVIDER=eskiz`, `ESKIZ_EMAIL`, `ESKIZ_PASSWORD`, `ESKIZ_FROM`, `SMS_TEMPLATE` (Eskiz'da tasdiqlangan matn), `SMS_DAILY_CAP` (sutkada jami) va `SMS_8HOUR_CAP` (8 soatda jami, 0 — o'chirilgan) ni to'ldiring.
Bu limitlar BUTUN tizim bo'yicha (hamma foydalanuvchilar uchun umumiy) va hisobdagi pulni tugatib qo'yishdan himoya qiladi. Limit tugasa, yangi kod so'rash vaqtincha to'xtaydi.
Haqiqiy SMS faqat `APP_ENV=production` da yuboriladi (boshqa muhitda OTP doim `123456`).

Tekshirish (bitta haqiqiy SMS, o'z raqamingizga; hisobdan pul yechiladi, limitlarga kirmaydi):
`cd backend && python3 -m app.tools.sms_check 901234567 --env-file ../.env`

Server: `uvicorn app.main:create_app --factory --env-file ../.env`.
Login/parol faqat serverning `.env` faylida; Git'ga, chatga yoki log'ga yozilmaydi.

### Deploy (Render.com, Docker)
1. Eskiz paroli chatga/Git'ga tushgan bo'lsa — avval Eskiz kabinetida **parolni almashtiring**.
2. Render → **New → Blueprint** → `AkmaljonMuminov/tezyubor` repozitoriyasini tanlang (`render.yaml` o'qiladi).
3. Render paneli → `tezyubor-api` → **Environment**: `ESKIZ_EMAIL` va `ESKIZ_PASSWORD` ni kiriting (`JWT_SECRET`/`OTP_SECRET` avtomatik yaratiladi).
4. Deploy tugagach `https://<nom>.onrender.com/health` → `{"status":"ok","test_mode":false}` bo'lishi kerak.
5. GitHub → Actions → **Build APK** → Run workflow: `api_mode=real`, `api_base_url=https://<nom>.onrender.com`.

Cheklovlar: bepul Render xizmati 15 daqiqa so'rovsiz uxlaydi (birinchi so'rov ~30–60 s); backend bitta jarayon va xotirada ishlaydi (restartda foydalanuvchilar yo'qoladi); Eskiz chet el IP'lardan kelgan so'rovni rad etishi mumkin — shunda O'zbekistondagi serverga ko'chirish kerak.

## Mobil

```bash
cd mobile
flutter create --org uz.tezyubor --project-name tezyubor_mobile .   # android/ios papkalarini yaratadi
rm -f test/widget_test.dart          # flutter create qo'shgan standart testni o'chiring (MyApp yo'q)
# android/app/build.gradle(.kts): applicationId = "uz.tezyubor.app"
flutter pub get
flutter analyze && flutter test
flutter run                          # API_MODE=mock (standart)
# Backend bilan: flutter run --dart-define=API_MODE=real --dart-define=API_BASE_URL=http://10.0.2.2:8000
# (Android emulyatorda http:// uchun cleartext ruxsati kerak; production'da faqat https)
```

Ikonka PNG'lari: `assets/brand/app_icon*.svg` ni 1024px PNG ga eksport qilib `flutter_launcher_icons` bilan ulang (keyingi bosqich).

## Xavfsizlik qoidalari
`.env` va kalitlar Git'ga qo'shilmaydi (`.gitignore`). Maxfiy qiymatlar kodda yo'q: `JWT_SECRET`/`OTP_SECRET` bo'lmasa backend ishga tushmaydi.
