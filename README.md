# Tezyubor

Mobil to'lov ilovasi (Android/iOS). Texnologiyalar: Flutter, FastAPI, PostgreSQL, Redis, React (admin).

## Holat (3-bosqich)

| Qism | Holat |
|---|---|
| Grafikalar: premium kit (navy/royal/oltin, T logotip, 25 ikonka, bannerlar, launcher ikonka) | ✅ Asl kit `design/premium_kit`, ilova uchun tozalangani `mobile/assets` (SVG ichida matn/pattern/filtr yo'q — Flutter chizmaydi). Telefon ekranida ko'rinishi odam ko'zi bilan tekshirilmagan |
Loyiha yopildi 
| Flutter: splash, telefon, OTP, PIN yaratish/kirish | ⚠️ Yozilgan, **ishga tushirib tekshirilmagan** |
| Flutter: bosh sahifa, kartalar, tarix, kartaga o'tkazma, to'lovlar (mobil/kommunal) | ⚠️ Yozilgan (**mock ma'lumot**), ishga tushirib tekshirilmagan |
| Flutter: pastki navigatsiya (Asosiy, O'tkazmalar, To'lov, Monitoring, Profil) | ⚠️ Yozilgan, ishga tushirib tekshirilmagan |
| Flutter: monitoring (oylik tushum/xarajat, filtr, kunlar bo'yicha), so'nggi qabul qiluvchilar, kartalar orasida o'tkazma | ⚠️ Yozilgan (mock), ishga tushirib tekshirilmagan |
| Flutter: profil (maskalangan telefon), balansni yashirish, chiqish | ⚠️ Yozilgan. Chiqish faqat qurilmadagi tokenlarni o'chiradi, serverda bekor qilish endpointi yo'q |
| Flutter: To'lov bo'limi — qidiruv, 20 kategoriya, tanlangan to'lovlar, mobil operatorlar (telefon qatori), kommunal variantlar, elektr uchun hudud + ETK tanlash, xizmat bo'yicha tarix | ⚠️ Yozilgan (mock). Operator/xizmat nomlari faqat ko'rsatish uchun, ular bilan haqiqiy integratsiya yo'q. ETK ro'yxati faqat Samarqand uchun test ma'lumoti, qolgan hududlarda "tez orada"; boshqa kategoriyalar "Tez orada" |
| Flutter: chek — to'lovdan keyin va tarixdan ochiladi, tafsilotlar (karta maskalangan), matnni nusxalash | ⚠️ Yozilgan. Test rejimida chekda "TEST CHEK — haqiqiy to'lov emas" yozuvi bor. PDF/rasm sifatida ulashish yo'q |
| Flutter: haqiqiy HTTP klient (`API_MODE=real`) — kirish (haqiqiy SMS kod); hamyon baribir TEST | ⚠️ Yozilgan, klient testlari soxta HTTP bilan. Haqiqiy backend + telefon bilan **birga sinalmagan** |
| Flutter testlar (`validators`, `wallet`, `http_auth`) | ⚠️ Yozilgan, ishga tushirilmagan (CI'da `flutter test` ishlaydi, natijasi build'ni to'xtatmaydi) |
| Backend auth yadrosi (OTP, tokenlar, PIN, audit) | ✅ unit testlar o'tgan (CI: Backend tests) |
| Backend: SMS yuborish (Eskiz.uz) — token, qayta urinish, shablon, sutkalik limit, xatoda limitni qaytarish | ⚠️ Yozilgan, testlar (soxta HTTP bilan). **Haqiqiy Eskiz hisobi bilan jonli sinalmagan** — `python3 -m app.tools.sms_check <telefon>` bilan tekshiring |
| Backend HTTP qatlami (`router.py`, `main.py`): OTP → tasdiqlash → PIN → token aylanishi, xato formati, productionda `/docs` yopiq | ✅ CI'da haqiqiy FastAPI (`TestClient`) bilan sinalgan, SMS soxta yuboruvchi bilan |
| Backend: karta, o'tkazma, to'lov, tarix modullari | ❌ Yo'q (hamyon hozircha faqat mobil mock) |
| Biometrika, PIN tiklash, OTP qayta yuborish, o'tkazmada PIN tasdig'i | ❌ Boshlanmagan |
| Docker (`backend/Dockerfile`), Render (`render.yaml`) | ⚠️ CI'da image yig'iladi va `/health` tekshiriladi; **jonli deploy qilinmagan** |
| PostgreSQL/Redis, admin panel | ❌ Boshlanmagan. Backend ma'lumoti xotirada: server qayta ishga tushsa foydalanuvchilar va PIN yo'qoladi (qayta SMS bilan kirish kerak) |
| APK | ✅ GitHub Actions (`Build APK`), `.github/workflows/build-apk.yml` |

**Mock/test:** `API_MODE=mock` (standart) — OTP kodi `123456`, backendga ulanmaydi; balanslar, kartalar va tarix SOXTA (ilovada "TEST REJIMI" banneri bor).
`API_MODE=real` — kirish haqiqiy backend (`/v1/auth/*`) va haqiqiy SMS bilan; hamyon (kartalar, balans, to'lov, tarix) esa **baribir SOXTA** va ilovada "TEST HAMYON" banneri hamda "TEST CHEK" yozuvi turadi.
**Haqiqiy integratsiyalar yo'q:** SMS provayder, bank/protsessing, Uzcard/Humo, to'lov provayderlari — shartnoma va kalit kerak.

**Pul qoidalari (mobil):** summa tiynda `int` (double emas); har operatsiya uchun `Idempotency-Key` (kiritish o'zgarsa yangilanadi, qayta urinishda o'sha); komissiya/chegara serverda ham qayta tekshirilishi shart.

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
Loyiha yopildi 