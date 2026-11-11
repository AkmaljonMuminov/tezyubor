# Tezyubor

Mobil to'lov ilovasi (Android/iOS). Texnologiyalar: Flutter, FastAPI, PostgreSQL, Redis, React (admin).

## Holat (1-bosqich)

| Qism | Holat |
|---|---|
| Grafikalar (SVG, matnsiz, Tezyubor brendi) | ✅ `mobile/assets` |
| Flutter: splash, telefon, OTP, PIN yaratish/kirish | ⚠️ Yozilgan, **ishga tushirib tekshirilmagan** (muhitda Flutter SDK yo'q) |
| Flutter test (`validators_test.dart`) | ⚠️ Yozilgan, ishga tushirilmagan |
| Backend auth yadrosi (OTP, tokenlar, PIN, audit) | ✅ 41 ta unit test o'tgan |
| Backend HTTP qatlami (`router.py`, `main.py`) | ⚠️ Yozilgan, **tekshirilmagan** (fastapi o'rnatilmagan edi) |
| Bosh sahifa, kartalar, o'tkazma, to'lovlar, tarix, profil | ❌ Boshlanmagan |
| Biometrika, PIN tiklash, OTP qayta yuborish tugmasi | ❌ Boshlanmagan |
| PostgreSQL/Redis, Docker, CI/CD, admin panel | ❌ Boshlanmagan |
| APK/AAB | ❌ Flutter SDK kerak (sizning kompyuteringizda) |

**Mock/test:** mobil ilova `API_MODE=mock` da ishlaydi (OTP kodi `123456`, backendga ulanmaydi). Haqiqiy HTTP klient 2-bosqichda.
**Haqiqiy integratsiyalar yo'q:** SMS provayder, bank/protsessing, Uzcard/Humo, to'lov provayderlari — shartnoma va kalit kerak.

## Backend

```bash
cd backend
python3 -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
cp ../.env.example ../.env     # JWT_SECRET va OTP_SECRET ni to'ldiring (kamida 32 belgi, har xil)
python3 -m unittest discover -s tests -t . -v        # yoki: pytest
export $(grep -v '^#' ../.env | xargs) && uvicorn app.main:create_app --factory --reload
```

## Mobil

```bash
cd mobile
flutter create --org uz.tezyubor --project-name tezyubor_mobile .   # android/ios papkalarini yaratadi
rm -f test/widget_test.dart          # flutter create qo'shgan standart testni o'chiring (MyApp yo'q)
# android/app/build.gradle(.kts): applicationId = "uz.tezyubor.app"
flutter pub get
flutter analyze && flutter test
flutter run                          # API_MODE=mock (standart)
```

Ikonka PNG'lari: `assets/brand/app_icon*.svg` ni 1024px PNG ga eksport qilib `flutter_launcher_icons` bilan ulang (keyingi bosqich).

## Xavfsizlik qoidalari
`.env` va kalitlar Git'ga qo'shilmaydi (`.gitignore`). Maxfiy qiymatlar kodda yo'q: `JWT_SECRET`/`OTP_SECRET` bo'lmasa backend ishga tushmaydi.
