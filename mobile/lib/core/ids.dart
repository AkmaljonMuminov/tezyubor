import 'dart:math';

/// Pul operatsiyasi uchun Idempotency-Key. Bir operatsiya (ekran) uchun BIR marta yaratiladi
/// va qayta urinishda o'sha kalit yuboriladi — shunda tarmoq uzilsa ham pul ikki marta yechilmaydi.
String newIdempotencyKey() {
  final rnd = Random.secure();
  final bytes = List<int>.generate(16, (_) => rnd.nextInt(256));
  return bytes.map((b) => b.toRadixString(16).padLeft(2, '0')).join();
}
