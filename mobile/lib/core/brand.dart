/// Brend sozlamalari yagona joyda. Nom/shior shu yerdan olinadi (SVG ichiga yozilmaydi).
class AppBrand {
  const AppBrand._();

  static const String name = 'Tezyubor';
  static const String tagline = "To'lovlar va pul o'tkazmalari";
  static const String appId = 'uz.tezyubor.app';
}

/// `--dart-define=API_MODE=mock` (standart) — backendsiz test rejimi.
/// `--dart-define=API_MODE=real` — haqiqiy backend (hozircha faqat auth: `/v1/auth/*`).
const String kApiMode = String.fromEnvironment('API_MODE', defaultValue: 'mock');
const bool kMockMode = kApiMode == 'mock';

/// Backend manzili. Android emulyatorda kompyuter `10.0.2.2`. Production'da FAQAT https.
const String kApiBaseUrl = String.fromEnvironment('API_BASE_URL', defaultValue: 'http://10.0.2.2:8000');
