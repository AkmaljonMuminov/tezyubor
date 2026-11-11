import 'package:flutter_test/flutter_test.dart';
import 'package:tezyubor_mobile/core/validators.dart';

void main() {
  group('normalizePhone', () {
    test('9 xonali raqamga 998 qo\'shadi', () {
      expect(normalizePhone('90 123 45 67'), '998901234567');
    });
    test('+998 bilan ham qabul qiladi', () {
      expect(normalizePhone('+998 90 123 45 67'), '998901234567');
    });
    test('noto\'g\'ri uzunlik yoki 0 bilan boshlansa null', () {
      expect(normalizePhone('12345'), isNull);
      expect(normalizePhone('012345678'), isNull);
      expect(normalizePhone(''), isNull);
    });
  });

  group('isPinAcceptable', () {
    test('oddiy PIN rad etiladi', () {
      for (final p in ['1111', '0000', '1234', '4321', '3456', '12a4', '123', '12345']) {
        expect(isPinAcceptable(p), isFalse, reason: p);
      }
    });
    test('oddiy bo\'lmagan PIN qabul qilinadi', () {
      for (final p in ['1357', '2580', '7391', '1122']) {
        expect(isPinAcceptable(p), isTrue, reason: p);
      }
    });
  });
}
