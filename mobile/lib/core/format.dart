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

const List<String> _monthsUz = [
  'yanvar', 'fevral', 'mart', 'aprel', 'may', 'iyun',
  'iyul', 'avgust', 'sentabr', 'oktabr', 'noyabr', 'dekabr',
];

/// `Bugun` / `Kecha` / `9 noyabr 2026`. [day] va [now] kun boshiga keltiriladi.
String dayLabel(DateTime day, DateTime now) {
  final d = DateTime(day.year, day.month, day.day);
  final today = DateTime(now.year, now.month, now.day);
  final diff = today.difference(d).inDays;
  if (diff == 0) return 'Bugun';
  if (diff == 1) return 'Kecha';
  return '${d.day} ${_monthsUz[d.month - 1]} ${d.year}';
}

/// `13:36`
String formatTime(DateTime t) {
  final l = t.toLocal();
  String two(int n) => n.toString().padLeft(2, '0');
  return '${two(l.hour)}:${two(l.minute)}';
}

/// `901234567` -> `+998 90 123 45 67`. 9 xonali bo'lmasa o'zgartirmaydi.
String formatPhone9(String digits) {
  if (!RegExp(r'^\d{9}$').hasMatch(digits)) return digits;
  return '+998 ${digits.substring(0, 2)} ${digits.substring(2, 5)} ${digits.substring(5, 7)} ${digits.substring(7)}';
}
