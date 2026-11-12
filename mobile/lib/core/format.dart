/// `dd.MM.yyyy HH:mm` (intl paketisiz, mahalliy vaqt).
String formatDateTime(DateTime t) {
  final l = t.toLocal();
  String two(int n) => n.toString().padLeft(2, '0');
  return '${two(l.day)}.${two(l.month)}.${l.year} ${two(l.hour)}:${two(l.minute)}';
}

/// Karta raqamini `XXXX XXXX XXXX XXXX` ko'rinishida guruhlaydi (kiritish paytida).
String groupDigits(String digits, {int group = 4}) {
  final buf = StringBuffer();
  for (var i = 0; i < digits.length; i++) {
    if (i > 0 && i % group == 0) buf.write(' ');
    buf.write(digits[i]);
  }
  return buf.toString();
}
