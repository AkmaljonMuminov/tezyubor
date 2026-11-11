/// Telefonni `998XXXXXXXXX` ko'rinishiga keltiradi. Noto'g'ri bo'lsa `null`.
/// Eslatma: server ham shu qoidalarni qayta tekshiradi (klient ishonchli emas).
String? normalizePhone(String raw) {
  var digits = raw.replaceAll(RegExp(r'\D'), '');
  if (digits.length == 9) digits = '998$digits';
  if (!RegExp(r'^998[1-9][0-9]{8}$').hasMatch(digits)) return null;
  return digits;
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
