import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:tezyubor_mobile/core/brand.dart';
import 'package:tezyubor_mobile/core/l10n/strings.dart';
import 'package:tezyubor_mobile/shared/test_mode_banner.dart';

void main() {
  test('hamyon backendi yo\'qligi uchun hamyon har doim soxta (API_MODE=real da ham)', () {
    expect(kWalletIsMock, isTrue);
  });

  testWidgets('TEST banneri hamyon soxta ekanini ko\'rsatadi', (tester) async {
    await tester.pumpWidget(const MaterialApp(home: Scaffold(body: TestModeBanner())));
    // mock rejimda: "haqiqiy SMS yo'q"; real rejimda: "TEST HAMYON" (SMS haqiqiy, hamyon soxta)
    final expected = kMockMode ? Strings.testMode : Strings.testWalletMode;
    expect(find.text(expected), findsOneWidget);
  });

  test("real rejimda banner matni SMS haqida yolg'on gapirmaydi", () {
    expect(Strings.testWalletMode, isNot(contains('SMS')));
    expect(Strings.testMode, contains('SMS'));
  });
}
