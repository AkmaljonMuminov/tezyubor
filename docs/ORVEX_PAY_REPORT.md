# ORVEX PAY brendlash — build va tekshiruv hisoboti

Sana: 2026-11-14. Branch: `feature/orvex-pay-branding` (asosi `feature/anorbank-integration` @ `5d6cc50`; `main` ga tegilmagan, PR ochilmagan).
Zaxira: branch `backup/pre-orvex-pay-2026-11-14` (= `5d6cc50`).

## APK (haqiqiy CI build)

| | |
|---|---|
| Workflow / run | `Build APK`, run **43608211409**, commit **c1d1ddc** (kod jihatidan branch'ning oxirgi holati) |
| Artefakt | `orvex-pay-apk` (id 14118722750, ichida `app-release.apk`), 90 kun saqlanadi |
| Havola (GitHub'ga kirgan holda) | https://github.com/AkmaljonMuminov/tezyubor/actions/runs/43608211409/artifacts/14118722750 |
| Hajmi / SHA-256 | 54 271 670 bayt / `181b2c37adaabbc60be0590e1c17aaff9b5aded4a1b100bca254890caf630d8d` |
| Rejim | `API_MODE=mock` (backendsiz test rejimi; hamyon har doim sandbox/TEST) |

`aapt2 dump badging` (CI logidan): `package: name='uz.tezyubor.app'`, `application-label:'ORVEX PAY'`. Ikkalasi CI'da qat'iy tekshiriladi (mos kelmasa build yiqiladi).

## Build va testlar

| Bosqich | Natija |
|---|---|
| `flutter analyze` | xato/ogohlantirish **yo'q**; 36 ta `info` (35 tasi avvaldan: `package:flutter/material.dart` Flutter 3.50 da eskirgan; 1 tasi yangi `brand_test.dart` dagi shu xil) |
| `flutter test` | **88 test o'tdi** (82 mavjud + 6 yangi `brand_test.dart`), 0 yiqilgan |
| `flutter build apk --release` | muvaffaqiyatli |
| Android patchlar | `android:label="ORVEX PAY"`, `windowSplashScreenBackground`, `launch_background.xml` (+ oldingi: `USE_BIOMETRIC`, `allowBackup=false`, `FlutterFragmentActivity`, AppCompat) — log bilan tasdiqlangan |
| Backend tests | ishga tushmadi: backend o'zgarmagan (so'nggi yashil run 43548053603, 228 test, commit `39e0df7` dan beri `backend/` farqi yo'q) |

Halol qayd: birinchi urinish (run 43607637198) APK yig'di, lekin `analyze` 1 xato topdi: yangi testimda `dart:typed_data` importi yo'q edi (`ByteData`). `analyze`/`test` bosqichlari `continue-on-error` bo'lgani uchun run "yashil" ko'rindi — logni o'qib topdim va tuzatdim (commit `c1d1ddc`). Mavjud testlar o'zgartirilmagan; faqat yangi test fayli qo'shilgan.

## Backend va biznes mantiqqa tegilmagani (git diff)

Taqqoslash: `git diff 5d6cc50..HEAD` (73 fayl, +669 / −19):

```
git diff --stat 5d6cc50..HEAD -- backend admin render.yaml .env.example \
  mobile/lib/core/network mobile/lib/core/security mobile/lib/features/auth \
  mobile/lib/features/wallet mobile/lib/core/router.dart
→ (bo'sh)
```

`mobile/lib` da o'zgargan faqat 6 fayl: `core/assets.dart`, `core/brand.dart`, `core/l10n/strings.dart` (2 matn), `core/theme/app_colors.dart` (izoh), `features/splash/splash_screen.dart` (fon + shior rangi), `shared/brand_widgets.dart` (`NavyBackground` ga ixtiyoriy `asset` parametri, shior rangi). Boshqa: `mobile/pubspec.yaml` (faqat `description`).

## O'zgargan fayllar (guruhlab)

- Grafika (mobil): `mobile/assets/brand/logo.png` (almashdi), `mobile/assets/brand/splash_bg.svg` (yangi), `mobile/launcher_res/mipmap-*/ic_launcher{,_background,_foreground}.png` (15 ta almashdi), `launcher_res/drawable{,-v21}/launch_background.xml`, `launcher_res/drawable-nodpi/launch_logo.png`, `launcher_res/values/orvex_colors.xml` (yangi)
- Kod (brend): yuqoridagi 6 fayl + `mobile/pubspec.yaml`
- Test: `mobile/test/brand_test.dart` (yangi)
- CI: `.github/workflows/build-apk.yml` (ilova nomi, native splash rangi, APK tekshiruvi, artefakt nomi)
- Dizayn kiti: `design/orvex_pay_kit/**` (39 fayl, ZIP'dagi asl + `tools/render_brand_assets.js`)
- Hujjat: `README.md`, `docs/ARCHITECTURE.md`, `docs/BRANDING.md`, `docs/ORVEX_PAY_REPORT.md`

## TekshirilMAGAN

- APK baytlarini men yuklab ololmadim (sandbox tarmoq ruxsat ro'yxati GitHub artefakt saqlagichini bloklaydi); metama'lumot CI'dagi `aapt2` chiqishiga tayanadi.
- Launcher ikonka maskalari (doira/skvirkl), native splash, yangi splash/AuthHeader ko'rinishi **haqiqiy telefonda ko'rilmagan**. Ikonka PNG'lari faqat kompyuterda chizilgan kontakt varaqda ko'zdan kechirilgan.
- Barmoq izi (oldingi bosqich) hali ham qurilmada sinalmagan.

## Ochiq masalalar

Qarang: `docs/BRANDING.md` — SMS matni (`SMS_TEMPLATE`), serverdagi sessiya qurilma nomi, backend `/docs` sarlavhasi, kitdagi nomuvofiqliklar (eski "T" preview PNG, social shablonlarda eski shior, oltin urg'ular).
