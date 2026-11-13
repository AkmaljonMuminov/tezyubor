/// Grafika yo'llari. Manba: `design/premium_kit` (Flutter uchun tozalangan: SVG ichida matn, pattern va filtr yo'q —
/// matnlar vidjetlarda beriladi). Ikonkalarda oltin gradient SVG'ning o'zida; ularni [ServiceIcon] navy fonda ko'rsatadi.
class AppAssets {
  const AppAssets._();

  // Brend
  static const logo = 'assets/brand/logo.png'; // tasdiqlangan ikonka (yumaloq burchakli, shaffof)
  static const bgNavy = 'assets/backgrounds/premium_navy.svg';

  // Ikonkalar
  static const icHome = 'assets/icons/home.svg';
  static const icTransfer = 'assets/icons/transfer.svg';
  static const icMobile = 'assets/icons/mobile.svg';
  static const icBills = 'assets/icons/utilities.svg';
  static const icPayments = 'assets/icons/payments.svg';
  static const icQr = 'assets/icons/qr.svg';
  static const icCard = 'assets/icons/cards.svg';
  static const icHistory = 'assets/icons/history.svg';
  static const icAnalytics = 'assets/icons/analytics.svg';
  static const icCashback = 'assets/icons/gift.svg';
  static const icProfile = 'assets/icons/profile.svg';

  // Bannerlar (faqat fon; matn [PromoBanner] da)
  static const bannerWelcome = 'assets/banners/banner_welcome.svg';
  static const bannerTransfer = 'assets/banners/banner_transfer.svg';
  static const bannerSafety = 'assets/banners/banner_safety.svg';
  static const bannerRewards = 'assets/banners/banner_rewards.svg';
}
