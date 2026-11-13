/// Brend sozlamalari yagona joyda. Nom/shior shu yerdan olinadi (SVG ichiga yozilmaydi).
class AppBrand {
  const AppBrand._();

  static const String name = 'Tezyubor';
  static const String tagline = "To'lovlar va pul o'tkazmalari";
  static const String appId = 'uz.tezyubor.app';
  static const String wordmark = 'TEZYUBOR';
  static const String slogan = 'Tez. Oson. Ishonchli.';
}

/// `--dart-define=API_MODE=mock` (standart) — backendsiz test rejimi.
/// `--dart-define=API_MODE=real` — haqiqiy backend bilan kirish (`/v1/auth/*`, haqiqiy SMS kod).
const String kApiMode = String.fromEnvironment('API_MODE', defaultValue: 'mock');

/// Kirish (auth) soxta: SMS yuborilmaydi, kod doim 123456.
const bool kMockMode = kApiMode == 'mock';

/// Hamyon (kartalar, balans, o'tkazma, to'lov, tarix) HOZIRCHA HAR DOIM soxta — hamyon backendi yo'q.
/// `API_MODE=real` bo'lsa ham shunday: ilova "TEST" belgilarini ko'rsatib turadi, shunda soxta
/// balans haqiqiy pul deb o'ylanmaydi. Hamyon backendi tayyor bo'lganda shu qiymat `false` bo'ladi.
const bool kWalletIsMock = true;

/// Backend manzili. Android emulyatorda kompyuter `10.0.2.2`. Production'da FAQAT https.
const String kApiBaseUrl = String.fromEnvironment('API_BASE_URL', defaultValue: 'http://10.0.2.2:8000');
