# ORVEX PAY — brendlash (Tezyubor → ORVEX PAY)

Holat: 2026-11-14, branch `feature/orvex-pay-branding` (asosi: `feature/anorbank-integration`).
Zaxira: branch `backup/pre-orvex-pay-2026-11-14` (brendlashdan oldingi holat).

Shart: **faqat grafika va foydalanuvchiga ko'rinadigan brend matnlari**. Backend, auth, pul harakati, Security Guard, SMS, paket nomi (`applicationId`) o'zgarmaydi.

## Nima o'zgardi

| Joy | Oldin | Hozir |
|---|---|---|
| Launcher'dagi ilova nomi (`android:label`) | `tezyubor_mobile` | `ORVEX PAY` (CI'da `AndroidManifest.xml` patch'i; mos kelmasa build yiqiladi) |
| `AppBrand.name` / `wordmark` | `Tezyubor` / `TEZYUBOR` | `ORVEX PAY` / `ORVEX PAY` |
| `AppBrand.slogan` | `Tez. Oson. Ishonchli.` | `TEZ • XAVFSIZ • QULAY` (rangi cyan — yangi `splash_screen.svg` dagidek) |
| Bosh sahifa banneri sarlavha osti | `Tez. Oson. Ishonchli.` | `Tez. Xavfsiz. Qulay.` |
| Biometrik so'rov matni | `Tezyubor ilovasiga kirish…` | `ORVEX PAY ilovasiga kirish…` |
| Ilova ichidagi logo (`assets/brand/logo.png`) | eski "T" belgisi | `logo_mark.svg` dan chizilgan 512×512 PNG |
| Launcher ikonka (barcha zichliklar + adaptive) | "T" | `app_icon.svg` dan: eski (API<26) ikonka va adaptive (fon gradient + halqa/karta, xavfsiz zonaga sig'adi) |
| Splash (Flutter) | `premium_navy` fon | `assets/brand/splash_bg.svg` (`splash_screen.svg` ning gradient + halqasi; matn va belgi vidjetlarda) |
| Splash (native, Flutter chizguncha) | oq | `launch_background.xml`: Midnight Navy + `launch_logo.png`; Android 12+ da `windowSplashScreenBackground` |
| Chekdagi sarlavha | `Tezyubor — chek` | `ORVEX PAY — chek` (`AppBrand.name` dan; mantiq o'zgarmagan) |
| CI artefakt nomi | `tezyubor-apk` | `orvex-pay-apk` |

Dizayn kiti asl holda `design/orvex_pay_kit/` da (ZIP tarkibi, `approved_icon_preview.png` dan tashqari — pastga qarang). PNG'lar `design/orvex_pay_kit/tools/render_brand_assets.js` bilan SVG'lardan chiziladi (Chromium/Playwright).

## Ataylab O'ZGARTIRILMAGAN

- `applicationId` = `uz.tezyubor.app` (CI `build-apk.yml` va `AppBrand.appId`), Dart paket nomi `tezyubor_mobile`, `flutter create --org uz.tezyubor`. Test `test/brand_test.dart` shuni qo'riqlaydi; CI APK ichidagi paket nomini `aapt2` bilan tekshiradi.
- Backend (`backend/`), `admin/`, migratsiyalar, auth/OTP/PIN/JWT, hamyon, Security Guard — bitta bayt ham.
- Kod ichidagi ichki nomlar: `TezyuborApp` klassi, repozitoriy nomi, Render xizmati `tezyubor-api`, test bazasi nomi.

## Eski nom hali ko'rinadigan joylar (taqiqlangan hududda — sizning qaroringiz kerak)

1. **SMS matni**: `Tezyubor tasdiqlash kodi: {code}…` — `backend/app/config.py` standarti, `.env.example`, `render.yaml` (`SMS_TEMPLATE`). Kod o'zgarmaydi: Render panelida `SMS_TEMPLATE` muhit o'zgaruvchisini o'zgartirish yetadi. Eslatma: Eskiz'da shablonlar odatda moderatsiyadan o'tadi — yangi matn tasdiqlanmaguncha SMS yetib bormasligi mumkin.
2. **Qurilma nomi** serverdagi "Sessiyalar" ro'yxatida: `Tezyubor (android)` — `http_auth_repository.dart` (auth kodi).
3. **Backend**: FastAPI `title="Tezyubor API"` (`/docs` sahifasi), log nomlari `tezyubor.*`.

## To'plamdagi nomuvofiqliklar (tuzatilmadi, bilib qo'ying)

- `brand/approved_icon_preview.png` — bu **eski "T" ikonkasi**, ORVEX PAY emas. Ishlatilmadi va `design/orvex_pay_kit/` ga ko'chirilmadi.
- `social/*` shablonlarida shior hali eski: `TEZ • OSON • ISHONCHLI` (siz bergan yangi shior `TEZ • XAVFSIZ • QULAY`). Ilovada ishlatilmaydi; kitda o'zgartirilmagan.
- `docs/DESIGN_SYSTEM.md` palitradan oltinni olib tashlagan, lekin kitdagi **ikonkalar va bannerlar oltin gradientli** (eski kit bilan bayt-ma'bayt bir xil). Ilova temasida ham oltin urg'ular qolgan (navigatsiya tanlovi, badge'lar). Yangi palitraga to'liq o'tish uchun ular cyan/royal'ga almashtirilishi kerak — alohida qaror.
- `icons/`, `backgrounds/`, `banners/` (`banner_rewards` dan tashqari) eski kit bilan bir xil, shuning uchun `mobile/assets` dagi tozalangan nusxalar o'zgarmadi. `banner_rewards` farqi faqat matnda (`<text>`), ilovaga kirmaydigan qism: ilovada banner matni vidjetda chiziladi.

## Tekshiruv

CI (`Build APK`): 1) `flutter analyze`, 2) `flutter test` (shu jumladan `brand_test.dart`), 3) APK yig'iladi, 4) `aapt2 dump badging`: `package: name='uz.tezyubor.app'` va `application-label:'ORVEX PAY'`. Natijalar PR/hisobotda. Qurilmada ko'z bilan tekshirilmagan: ikonka maskalari, native splash.
