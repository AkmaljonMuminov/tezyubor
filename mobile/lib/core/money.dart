/// Pul tiyinda (1 so'm = 100 tiyin) butun son sifatida saqlanadi. `double` pul uchun ishlatilmaydi.
const int kTiyinPerSom = 100;

/// `1234500` -> `12 345 so'm`. Tiyin bo'lsa `12 345,50 so'm`.
String formatSom(int tiyin, {bool signed = false}) {
  final negative = tiyin < 0;
  final abs = tiyin.abs();
  final som = (abs ~/ kTiyinPerSom).toString();
  final frac = abs % kTiyinPerSom;

  final buf = StringBuffer();
  for (var i = 0; i < som.length; i++) {
    if (i > 0 && (som.length - i) % 3 == 0) buf.write(' ');
    buf.write(som[i]);
  }
  if (frac != 0) buf.write(',${frac.toString().padLeft(2, '0')}');

  final sign = negative ? '−' : (signed ? '+' : '');
  return "$sign${buf.toString()} so'm";
}
