/// Brend sozlamalari yagona joyda. Nom/shior shu yerdan olinadi (SVG ichiga yozilmaydi).
class AppBrand {
  const AppBrand._();

  static const String name = 'Tezyubor';
  static const String tagline = "To'lovlar va pul o'tkazmalari";
  static const String appId = 'uz.tezyubor.app';
}

/// `--dart-define=API_MODE=mock` (standart) — backendsiz test rejimi.
/// Haqiqiy HTTP klient 2-bosqichda qo'shiladi; hozircha faqat `mock` ishlaydi.
const String kApiMode = String.fromEnvironment('API_MODE', defaultValue: 'mock');
const bool kMockMode = kApiMode == 'mock';
