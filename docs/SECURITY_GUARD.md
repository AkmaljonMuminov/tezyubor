# Tezyubor Security Guard: audit va amalga oshirish rejasi

## Audit xulosasi

Audit `work/phase-4-production` branchi yaratilgan paytdagi kodni tekshirdi. Flutter platforma loyihalari Git’da saqlanmagan; APK workflow `flutter create` bilan Android scaffold yaratadi. Mobil ilovada hozircha `flutter_secure_storage` bor, ammo WorkManager, PackageManager skaneri va Android security ekrani yo‘q.

FastAPI’da faqat `/v1/auth/*` endpointlari mavjud. Auth tokenlari foydalanuvchini aniqlaydi, lekin qurilma identifikatoriga bog‘lanmagan. Karta, transfer, withdrawal yoki boshqa moliyaviy backend endpointlari hali yo‘q; wallet faqat TEST sifatida ko‘rsatiladigan mobile mock.

PostgreSQL hozir ixtiyoriy va auth ma’lumotlarini saqlaydi. `Database.migrate()` startup paytida SQL sxemasini yaratadi; versiyalangan migration tizimi yo‘q. Audit log RAM’da. Shu sababli Security Guard cheklovlarini production’da ishonchli saqlash uchun PostgreSQL majburiy bo‘lishi va restriction/audit yozuvlari bazaga yozilishi kerak.

## Taklif qilingan backend o‘zgarishlar

- Authenticated `/api/v1/security/events`, `/status`, `/rescan` va `/recovery/request` endpointlari.
- `security_events`, `device_security_status`, `account_restrictions`, `security_recovery_requests` va append-only audit yozuvlari uchun PostgreSQL jadvallari.
- Event ID va idempotency key bo‘yicha takror yuborishni xavfsiz qayta ishlash; eskirgan/future timestamp va noto‘g‘ri formatlarni rad etish.
- Mijoz yuborgan `CLEAN` yoki `MALICIOUS` qiymatini haqiqat deb qabul qilmaslik. Faqat serverdagi tasdiqlangan SHA-256/signature IOC ro‘yxatiga moslik avtomatik `MALICIOUS` restriction berishi mumkin; boshqa natijalar `SUSPICIOUS` yoki `UNKNOWN` bo‘ladi.
- Markaziy middleware orqali `/api/v1` ostidagi barcha auth talab qiladigan route’larda restriction tekshiruvi. Security status/rescan/recovery va zarur auth yo‘llari cheklov ostida ham ishlashi kerak.
- Recovery so‘rovi cheklovni o‘zi yechmaydi. Yangi scan faqat manual review uchun dalil; unlock faqat serverdagi vakolatli operator qarori bilan, alohida audit yozuvi orqali bajariladi.

## Android yondashuvi va OS cheklovlari

- `QUERY_ALL_PACKAGES` qo‘shilmaydi. Android 11+ package visibility boshqa ilovalarni sukut bo‘yicha filtrlashi mumkin; shuning uchun inventory to‘liq bo‘lmaydi. Google Play o‘rnatilgan ilovalar ro‘yxatini shaxsiy va sezgir ma’lumot deb hisoblaydi, keng ruxsat esa siyosat tekshiruvini talab qiladi.
- PackageManager faqat ko‘rinadigan/maqsadli package’lar bo‘yicha tekshiriladi. Foydalanuvchi tanlagan APK SAF orqali qurilmaning o‘zida vaqtinchalik tahlil qilinishi mumkin; APK tarkibi backendga yuborilmaydi.
- WorkManager periodic task uzluksiz real-time monitoring kafolati emas. Android ish vaqtini batareya, Doze va scheduling sharoitiga qarab kechiktirishi mumkin; periodic minimum interval 15 daqiqa.
- Hash/signing certificate, ko‘rinadigan package ruxsatlari va install source faqat alomat hisoblanadi; ular yakka holda barcha malware’ni aniqlamaydi.
- Play Integrity'ni serverda tasdiqlash uchun Play Console/Google Cloud sozlamasi kerak. Repo'da bunday sozlama yo‘q, shuning uchun attestation yoqilgan deb hisoblanmaydi.

## Xatarlar va ushbu ishning chegaralari

- Hozircha tasdiqlangan malware hash/signature ro‘yxati berilmagan. Serverdagi IOC ro‘yxati bo‘sh bo‘lsa, avtomatik restriction yoqilmaydi; yangi yoki noma’lum zararli ilova `UNKNOWN` bo‘lib qolishi mumkin.
- O‘rnatilgan ilovalar ro‘yxati maxfiylikka taalluqli. Mahsulotni ommaga chiqarishdan oldin foydalanuvchining aniq roziligi, privacy disclosure va Google Play policy tekshiruvi kerak.
- Repository’da moliyaviy API yo‘q. Markaziy enforcement himoyalangan backend route’larda ishlaydi, ammo mobile mock wallet’ga server restriction ta’sir qilmaydi.
- Bu muhitda emulator yoki real Android qurilma, Play Integrity sozlamasi, Google Play review va release signing access tasdiqlanmagan; bajarilgan deb ko‘rsatilmaydi.

## Foydalanilgan rasmiy Android hujjatlari

- [Package visibility filtering](https://developer.android.com/training/package-visibility)
- [Google Play QUERY_ALL_PACKAGES policy](https://support.google.com/googleplay/android-developer/answer/10158779?hl=en)
- [WorkManager PeriodicWorkRequest](https://developer.android.com/reference/androidx/work/PeriodicWorkRequest)
- [Play Integrity: standard API request](https://developer.android.com/google/play/integrity/standard)
- [Storage Access Framework](https://developer.android.com/training/data-storage/shared/documents-files)
