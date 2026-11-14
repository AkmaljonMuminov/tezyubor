# AnorBank arxivi tahlili, xavfsizlik auditi va Tezyubor uchun reja

Sana: 2026-11-14 · Branch: `feature/anorbank-integration` (`main`dan ochilgan; `main`ga tegilmagan)

> Bu hujjat yakuniy xavfsizlik sertifikati **emas**. AnorBank kodi faqat o'qildi (ishga tushirilmadi, build qilinmadi);
> topilmalar fayl va qator bo'yicha tasdiqlangan, ammo ish vaqtidagi xatti-harakat kod o'qib baholangan.

## 1. AnorBank arxivi: arxitektura xaritasi

| Qatlam | Nima ishlatilgan |
|---|---|
| Til/UI | Kotlin, Jetpack Compose, Voyager (navigatsiya), Orbit MVI |
| DI | Hilt |
| Tarmoq | Retrofit 2.9 + OkHttp, Gson; `ChuckerInterceptor` |
| Saqlash | `SharedPreferences("prefferences")`, Room |
| Biometrika | `androidx.biometric` 1.2.0-alpha05 (`BioTouch.kt`) |
| API (`MyApi.kt`) | `v1/auth/{sign-up,sign-in,*/verify,*/resend,update-token,sign-out}`, `v1/card` (GET/POST), `v1/transfer/{card-owner,transfer,transfer/verify,history}` |
| Oqim | ro'yxatdan o'tish → SMS tasdiq → PIN o'rnatish → (barmoq izi) → PIN bilan kirish → bosh sahifa/kartalar/o'tkazma/tarix |

Ular ishlatadigan server — kimningdir test serveri (`http://195.158.16.140/mobile-bank/`), Tezyubor backend'iga **mos emas**:
endpoint nomlari, maydonlar (`sender-id`, `receiver-pan`, `amount: Int`) va javoblar boshqacha. Kod ko'chirilmaydi, faqat g'oyalar moslashtiriladi.

## 2. AnorBank'dan tasdiqlangan xavfli joylar (Tezyubor'ga KO'CHIRILMAYDI)

| # | Topilma | Dalil | Xavf |
|---|---|---|---|
| A1 | PIN `1234` kodga yozilgan | `presentation/auth/pins/PinScreens.kt:70` `const val password = "1234"` | Har kim kira oladi |
| A2 | PIN ochiq matnda, `==` bilan solishtiriladi, urinish limiti yo'q | `MyPreference.kt` (`PIN`, `code` kalitlari), `PinCodeModel.kt` | Qurilmadan PIN o'qiladi; cheksiz taxmin |
| A3 | PIN **log'ga yoziladi** (saqlangani ham, kiritilgani ham) | `PinCodeModel.kt:29,31` `Log.d("SSS", ...)` | `logcat` orqali PIN oshkor bo'ladi |
| A4 | Birinchi kiritilgan kod "PIN" bo'lib qoladi (tasdiqlash qadami yo'q) | `PinCodeModel.kt` (`getPinCOde()==""` → `setPinCode`) | Xato PIN bilan qulflanib qolish |
| A5 | Access/refresh/transfer token, karta PAN, qabul qiluvchi ismi, summa — oddiy `SharedPreferences`da | `MyPreference.kt`, `di/PreffModule.kt:21` | Root/backup orqali o'qiladi |
| A6 | `allowBackup="true"` + bo'sh backup qoidalari | `AndroidManifest.xml`, `res/xml/backup_rules.xml` | PIN/token bulutli zaxiraga tushadi |
| A7 | Faqat HTTP, `usesCleartextTraffic="true"`, yalang'och IP | `di/NetworkModule.kt`, `TokenAuthenticator.kt` | Parol, OTP, PAN tarmoqda ochiq (MITM) |
| A8 | Token yangilash: sinxronizatsiya yo'q, `runBlocking`, refresh token yo'q bo'lsa `!!` (NPE), muvaffaqiyatsizda sessiya tozalanmaydi | `TokenAuthenticator.kt`, `MyPreference.getRefreshToken()` | Parallel so'rovlarda refresh poygasi, crash |
| A9 | `Authorization` sarlavhasi oldindan qo'yilmaydi (`HeaderInterceptor` ro'yxatdan o'tmagan) | `di/NetworkModule.kt` | Kod o'qishdan xulosa: har so'rov 401 → refresh → qayta so'rov bo'lishi mumkin |
| A10 | Logout serverga aytilmaydi | `MyApi.signOut()` e'lon qilingan, hech qayerda chaqirilmagan | Token chiqishdan keyin ham yashaydi |
| A11 | Biometrika `CryptoObject`siz; `onAuthenticationFailed` ichida `onFailed` **chaqirilmaydi** (faqat nomi yozilgan); `FingerScreen` ham `Screen`, ham `FragmentActivity` | `BioTouch.kt`, `FingerScreen.kt` | Biometrika kalitga bog'lanmagan; xato callback ishlamaydi |
| A12 | Keraksiz ruxsatlar: aniq/taxminiy joylashuv, `READ_PHONE_STATE`, majburiy telefoniya | `AndroidManifest.xml` | Maxfiylik, Play Store rad etishi |
| A13 | Qabul qiluvchi kartasi PAN log'ga yoziladi | `TransactionModel.kt:74` `Log.d("TTT", "${data.pan}")` | PAN oshkor |
| A14 | O'tkazma so'rovida idempotentlik kaliti yo'q, summani klient yuboradi, komissiya ko'rinmaydi | `TransferRequest.kt` | Qayta yuborishda ikki marta yechilishi mumkin |
| A15 | `GetCardResponse` to'liq PAN va balansni klientga qaytaradi | `GetCardResponse.kt` | PAN keraksiz ochiladi |

**Yaxshi tomoni (adolat uchun):** Chucker faqat `debugImplementation`, release'da `library-no-op` (`app/build.gradle.kts:112-113`),
ya'ni HTTP inspektori release'ga tushmaydi. `isMinifyEnabled=false` esa release'da kod yashirilmasligini bildiradi.

## 3. Tezyubor'ning joriy holati (kod bilan tasdiqlangan)

| Funksiya | Hozir | Bo'shliq |
|---|---|---|
| OTP | HMAC xesh, limitlar, SMS cap. Challenge **xotirada** (`OtpChallenge`) | Restart/ko'p nusxada yo'qoladi → saqlash kerak |
| PIN | scrypt + constant-time, 5 xato → 15 daqiqa blok | Hisoblagich atomik emas (parallel so'rov bilan chetlab o'tiladi); blok eskalatsiyasi yo'q; 4 xonali PIN bazadan offline buziladi (pepper yo'q) |
| Token | Access JWT (10 daq), aylanuvchi refresh, qayta ishlatish aniqlanadi, oila bekor qilinadi | Access token sessiyaga bog'lanmagan (bekor qilingan sessiyada 10 daqiqa yashaydi); sessiyalar ro'yxati yo'q |
| Logout | Faqat lokal tozalash (`http_auth_repository.dart:82` izohda ham yozilgan) | **Serverda bekor qilish endpointi yo'q** |
| Mobil saqlash | `SecureTokenStore` (Keystore/Keychain) | Yaxshi; backup qoidalari tekshirilsin |
| Biometrika | Yo'q | Qo'shish kerak (PIN zaxira bilan) |
| Karta/o'tkazma/tarix | Faqat mobil mock (`kWalletIsMock=true`), backend yo'q | Backend modul kerak |
| Audit | Xotirada, cheksiz o'sadi | Chegaralash + bazaga yozish |
| Migratsiyalar | Bitta idempotent `SCHEMA` | Versiyalangan migratsiyalar |
| Xato formati | Yagona `{"error":{code,message}}` | Yaxshi, davom ettiriladi |

## 4. Funksiyalar jadvali: AnorBank → Tezyubor

| Funksiya | AnorBank | Tezyubor qarori |
|---|---|---|
| A. Biometrika | `BiometricPrompt`, CryptoObject yo'q | Flutter `local_auth`; qurilma imkoniyati tekshiriladi; **PIN zaxira**; faqat ilovani ochish uchun qulay yo'l (pul harakati PIN'ni serverda tasdiqlaydi). Kriptografik bog'lanmagani ochiq yoziladi |
| B. PIN | Ochiq matn, 1234 | Mavjud scrypt + atomik hisoblagich + eskalatsiyalanuvchi blok + ixtiyoriy server «pepper» + audit; PIN hech qachon log'ga yozilmaydi |
| C. Token/sessiya | Poyga, logout yo'q | Rotatsiya/reuse saqlanadi + **serverda logout**, sessiya ro'yxati, access token ↔ sessiya bog'lash; mobilda yagona-uchish (single-flight) refresh |
| D. Kartalar | Server noma'lum, to'liq PAN qaytadi | Backend: PAN **saqlanmaydi** (faqat `BIN6 + last4 + HMAC indeks`), CVV umuman olinmaydi, egalik/holat tekshiruvi, maskalangan chiqarish |
| E. O'tkazma | Klient summa yuboradi, idempotentlik yo'q | Backend summa/komissiya hisoblaydi, `Idempotency-Key`, holatlar, **PIN bilan tasdiq (serverda)**, atomik DB tranzaksiya, barcha javoblarda `sandbox: true` |
| F. Tarix/chek | Sahifalash bor | Backenddan, kursor sahifalash + filtr; chek faqat `completed` tranzaksiya uchun |

## 5. Rejalashtirilgan o'zgarishlar (fayllar)

**Backend (yangi/o'zgaradi)**
- `backend/app/migrations.py` (yangi) — versiyalangan migratsiyalar; `db.py` faqat shuni chaqiradi
- `backend/app/modules/auth/{stores,pg_stores,tokens,service,router,security,audit}.py` — sessiyalar, atomik PIN hisoblagich, pepper, audit
- `backend/app/modules/wallet/` (yangi) — `models, validators, store, pg_store, service, router`
- `backend/app/{config,main,errors}.py` — `PIN_PEPPER`, `WALLET_*` sozlamalari, yangi xatolar
- `backend/tests/` — yangi testlar (pastda), `.env.example` — faqat bo'sh o'rinbosarlar

**Mobil**
- `pubspec.yaml` (`local_auth`), `.github/workflows/build-apk.yml` (Android: `USE_BIOMETRIC`, `FlutterFragmentActivity`)
- `core/network/` (yagona-uchish refresh), `features/auth/` (logout → server, biometrik ochish), `features/profile/` (biometrik sozlamasi)

## 6. Bosqichli reja (har bosqich alohida commit, CI tekshiriladi)

1. **Hujjat** (shu fayl).
2. **Backend auth qotirish:** versiyalangan migratsiya → sessiyalar + `POST /v1/auth/logout` + `GET/DELETE /v1/auth/sessions` → access token `sid` ga bog'lanadi → atomik PIN hisoblagich + eskalatsiya + pepper → bounded/persist audit → OTP challenge'ni bazaga saqlash. Testlar.
3. **Backend wallet (sandbox):** kartalar → o'tkazma (idempotent, PIN tasdiq, atomik) → tarix/chek. Testlar (xotira + PostgreSQL CI).
4. **Mobil:** logout serverga, biometrik ochish (PIN zaxira), authenticated klient. Testlar (`flutter test`) — CI'da tekshiriladi.
5. **Yakuniy audit, PR, hisobot.**

## 7. Qabul qilingan cheklovlar va blokerlar (taxmin qilinmaydi)

| Blokerlik | Sabab |
|---|---|
| Haqiqiy bank/protsessing API | Shartnoma, kalitlar va hujjat yo'q → o'tkazma/kartalar faqat **sandbox**; ilova ichki «TEST» belgisi saqlanadi |
| Komissiya tarifi, limitlar | Biznes qaror. Sozlanadigan **o'rinbosar** qiymatlar (`TRANSFER_FEE_BPS=0` va h.k.), haqiqiy tarif keyin |
| PCI DSS | Hozir PAN saqlanmaydi va CVV olinmaydi — qamrov kichik. Haqiqiy karta ulanganda tokenizatsiya provayderi va rasmiy baholash kerak |
| Biometrikani kalitga bog'lash | `local_auth` bunga imkon bermaydi; Keystore `setUserAuthenticationRequired` kerak bo'lsa — alohida plugin/native kod |
| Mobil test | Bu muhitda Flutter yo'q; Dart kodi faqat GitHub Actions'da tekshiriladi |
| Backend HTTP/PG testlari | Bu muhitda `fastapi`/`psycopg` yo'q; ular faqat CI'da |

## 8. Test rejasi

OTP/PIN (blok, eskalatsiya, parallel urinish) · biometrik holatlar (mavjud emas/yozilmagan/vaqtincha/xato/bekor) · token refresh/reuse/revoke/logout · sessiya ro'yxati va boshqa foydalanuvchi sessiyasini o'chira olmaslik · karta qo'shish/o'chirish/noto'g'ri raqam (Luhn, muddat) · o'tkazma + komissiya · takroriy so'rov (idempotentlik) · yetarli mablag' yo'q · begona karta · tarix sahifalash · ruxsatsiz kirish (401) · xavfsizlik regressiyasi (log'da PIN/PAN/token yo'qligi).

## 9. Bajarilgan ishlar va joriy holat (yangilangan: 2026-11-14)

Tekshiruv manbalari: (1) GitHub Actions `Backend tests` (PostgreSQL 16 xizmati bilan), run 43548053603 — 228 test o'tgan, shu jumladan PostgreSQL shartnoma testlari va HTTP testlari. (2) `Build APK`, run 43575565749 (commit d6af83e) — `flutter analyze`: xato/ogohlantirish yo'q, 35 ta `info` (asosan `package:flutter/material.dart` eskirgan deb belgilangan — yangi Flutter 3.50, avvaldan bor); `flutter test`: **82 test o'tdi**; APK yig'ildi (54,5 MB).

| Reja bandi | Holat | Dalil / izoh |
|---|---|---|
| 1. Hujjat (shu fayl) | ✅ | commit `docs: AnorBank tahlili…` |
| 2. Backend auth qotirish: migratsiyalar, sessiyalar, `logout`, `sessions`, `sid` bog'lash | ✅ | A10 yopildi (serverda logout). `tests/test_hardening.py`, `test_wallet_http.SessionHttpTests` |
| 2. PIN: atomik hisoblagich, eskalatsiya, pepper (A2/A4 ning serverdagi ekvivalenti) | ✅ | parallel 30 ta taxmin — faqat 5 tasi tekshiriladi (`test_parallel_guesses_cannot_exceed_limit`) |
| 2. OTP challenge persistensiyasi | ✅ | `otp_challenges`, bir martalik iste'mol parallel testda tekshirilgan |
| 2. Audit: bounded + bazaga yozish | ✅ | `audit_log`; sink xatosi so'rovni buzmaydi |
| 3. Backend hamyon: kartalar | ✅ sandbox | PAN/CVV saqlanmaydi (A15 yopildi) |
| 3. O'tkazma: idempotent, serverda summa/komissiya, PIN tasdiq, atomik | ✅ sandbox | A14 yopildi. PostgreSQL'da: 6 parallel o'tkazma balansdan oshmaydi; bir o'tkazma 8 parallel tasdiqda bir marta yechiladi |
| 3. Tarix/chek | ✅ sandbox | kursor sahifalash (teng vaqtli yozuvlar bilan ham), chek faqat `completed` |
| 4. Mobil: logout serverga | ✅ CI | `HttpAuthRepository.logout()` → `POST /v1/auth/logout`; internet bo'lmasa ham qurilma tozalanadi. Testlar `test/biometric_test.dart` da, Build APK run 43575565749 |
| 4. Mobil: biometrika (PIN zaxira) | ✅ CI, qurilmada sinalmagan | `BiometricService` (`local_auth`), PIN ekranida avtomatik taklif + tugma, profilda yoqish. Faqat ilovani ochadi; pul harakati serverda PIN bilan. CI'da widget testlar o'tdi; Android sozlamalari qo'llanganini log tasdiqladi (`USE_BIOMETRIC`, `allowBackup=false`, `FlutterFragmentActivity`, AppCompat mavzusi). **Haqiqiy telefonda barmoq izi hali sinalmagan** |
| 4. Mobil: token yangilash poygasidan himoya (A8) | ✅ CI | `AuthedApiClient` (single-flight): parallel 6 so'rov → 1 ta yangilash (`test/authed_api_test.dart`). Hali hech bir ekran uni ishlatmaydi (hamyon mobilga ulanganda kerak bo'ladi) |
| 4. Mobil hamyonni backendga ulash | ❌ | qilinmagan. Mobil `WalletRepository` ko'p narsani talab qiladi (kommunal to'lovlar, saralanganlar), backendda ular yo'q — alohida reja kerak |
| 5. Yakuniy audit, PR, hisobot | ⏳ | mobil bosqichdan keyin |

**Haligacha ochiq (halol ro'yxat):**
- Haqiqiy bank/protsessing, Uzcard/Humo ulanishi — shartnoma va hujjat yo'q. Hamyon faqat sandbox.
- Komissiya, limit, boshlang'ich sinov balans qiymatlari — o'rinbosar, biznes qarori kerak.
- Mobil kod bu muhitda yig'ilmaydi (Flutter/Dart yo'q); `flutter analyze/test` natijasi faqat GitHub Actions'da ko'rinadi (run 43575565749 da yashil).
- Build APK workflow'ida `flutter analyze` va `flutter test` `continue-on-error`, ya'ni ular qizil bo'lsa ham APK yig'iladi — natijani Actions logidan alohida o'qish kerak.
- Qurilmadagi sinov (barmoq izi, haqiqiy Android) umuman bajarilmagan.
- `work/phase-4-production` bilan birlashtirishda faqat CI fayllari (`.github/workflows/backend-tests.yml`, `build-apk.yml`) to'qnashadi (men `feature/**` triggerini qo'shganman, u CI'ni qayta yozgan); `git merge-tree` bo'yicha README va `docs/` avtomatik birlashadi, lekin matn mazmunini (ikki tomon holat jadvalini) birlashtirgandan keyin ko'zdan kechirish kerak.
- `Docker Image CI` (GitHub shablon workflow'i) tuzatilmagan (ildizda Dockerfile yo'q); phase-4 branchida u o'chirilgan.
