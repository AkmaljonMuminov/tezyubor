/// Telefonni `998XXXXXXXXX` ko'rinishiga keltiradi. Noto'g'ri bo'lsa `null`.
/// Eslatma: server ham shu qoidalarni qayta tekshiradi (klient ishonchli emas).
String? normalizePhone(String raw) {
  var digits = raw.replaceAll(RegExp(r'\D'), '');
  if (digits.length == 9) digits = '998$digits';
  if (!RegExp(r'^998[1-9][0-9]{8}$').hasMatch(digits)) return null;
  return digits;
}

/// Karta raqamini 16 xonali raqamga keltiradi (Uzcard 8600 / Humo 9860, Luhn tekshiruvi bilan).
/// Noto'g'ri bo'lsa `null`. Server ham qayta tekshiradi.
String? normalizeCardNumber(String raw) {
  final d = raw.replaceAll(RegExp(r'\D'), '');
  if (d.length != 16) return null;
  if (!(d.startsWith('8600') || d.startsWith('9860'))) return null;
  return _luhnOk(d) ? d : null;
}

bool _luhnOk(String digits) {
  var sum = 0;
  var doubleIt = false;
  for (var i = digits.length - 1; i >= 0; i--) {
    var n = int.parse(digits[i]);
    if (doubleIt) {
      n *= 2;
      if (n > 9) n -= 9;
    }
    sum += n;
    doubleIt = !doubleIt;
  }
  return sum % 10 == 0;
}

/// Bir operatsiya chegaralari (tiyinda). Server ham shu chegaralarni qayta tekshiradi.
const int kMinAmountTiyin = 1000 * 100; // 1 000 so'm
const int kMaxAmountTiyin = 10000000 * 100; // 10 000 000 so'm

/// Foydalanuvchi kiritgan so'm summasini tiyinga o'giradi. Bo'sh, nol yoki chegaradan tashqari bo'lsa `null`.
int? parseAmountTiyin(String raw) {
  final digits = raw.replaceAll(RegExp(r'\D'), '');
  if (digits.isEmpty || digits.length > 10) return null;
  final som = int.tryParse(digits);
  if (som == null) return null;
  final tiyin = som * 100;
  if (tiyin < kMinAmountTiyin || tiyin > kMaxAmountTiyin) return null;
  return tiyin;
}

/// 4 xonali, bir xil raqamlardan (1111) yoki ketma-ketlikdan (1234, 4321) iborat bo'lmagan PIN.
bool isPinAcceptable(String pin) {
  if (!RegExp(r'^\d{4}$').hasMatch(pin)) return false;
  final d = pin.split('').map(int.parse).toList();
  if (d.toSet().length == 1) return false;
  final steps = <int>{for (var i = 0; i < 3; i++) d[i + 1] - d[i]};
  if (steps.length == 1 && (steps.first == 1 || steps.first == -1)) return false;
  return true;
}

/// `998901234567` -> `+998 90 *** ** 67` (ekranda to'liq raqam ko'rsatilmaydi).
String maskPhone(String normalized) {
  if (normalized.length != 12) return '+$normalized';
  return '+998 ${normalized.substring(3, 5)} *** ** ${normalized.substring(10)}';
}
