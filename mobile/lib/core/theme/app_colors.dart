import 'package:flutter/material.dart';

/// ORVEX PAY palitrasi (`design/orvex_pay_kit/docs/DESIGN_SYSTEM.md`):
/// midnight navy fon, royal blue asosiy tugmalar, cyan fokus, oltin faqat ajratib ko'rsatish uchun.
class AppColors {
  const AppColors._();

  // Brend ranglari
  static const Color navyDeep = Color(0xFF020A25);
  static const Color navy = Color(0xFF06143A);
  static const Color navyMid = Color(0xFF081B5B);
  static const Color royal = Color(0xFF123CFF);
  static const Color cyan = Color(0xFF18B8FF);
  static const Color gold = Color(0xFFFFB51B);
  static const Color goldLight = Color(0xFFFFCB45);
  static const Color silver = Color(0xFFF7FAFF);
  static const Color paleBlue = Color(0xFFC9D8FF);

  // Shaffof variantlar (withOpacity Flutter versiyalari orasida o'zgargani uchun tayyor qiymatlar)
  static const Color royalSoft = Color(0x73123CFF); // 45%
  static const Color cyanLine = Color(0x4018B8FF); // 25%
  static const Color paleBlueDim = Color(0xB3C9D8FF); // 70%
  static const Color royalShadow = Color(0x40123CFF); // 25%

  // Interfeys ranglari
  static const Color primary = royal;
  static const Color primaryDark = Color(0xFF0B2A9E);
  static const Color tint = Color(0xFFE6ECFF);
  static const Color text = Color(0xFF0B1534);
  static const Color muted = Color(0xFF5E6A8C);
  static const Color background = Color(0xFFF3F6FD);
  static const Color surface = Colors.white;
  static const Color success = Color(0xFF12A150);
  static const Color error = Color(0xFFD93636);
}
