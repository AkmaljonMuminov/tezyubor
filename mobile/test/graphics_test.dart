import 'dart:io';

import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:tezyubor_mobile/core/assets.dart';
import 'package:tezyubor_mobile/core/brand.dart';
import 'package:tezyubor_mobile/shared/brand_widgets.dart';
import 'package:tezyubor_mobile/shared/service_icon.dart';

void main() {
  const paths = [
    AppAssets.logo,
    AppAssets.bgNavy,
    AppAssets.icHome,
    AppAssets.icTransfer,
    AppAssets.icMobile,
    AppAssets.icBills,
    AppAssets.icPayments,
    AppAssets.icQr,
    AppAssets.icCard,
    AppAssets.icHistory,
    AppAssets.icAnalytics,
    AppAssets.icCashback,
    AppAssets.icProfile,
    AppAssets.bannerWelcome,
    AppAssets.bannerTransfer,
    AppAssets.bannerSafety,
    AppAssets.bannerRewards,
  ];

  test("AppAssets'dagi barcha fayllar mavjud", () {
    for (final p in paths) {
      expect(File(p).existsSync(), isTrue, reason: p);
    }
  });

  test("SVG'larda flutter_svg chizmaydigan elementlar yo'q (matn, pattern, filtr)", () {
    final svgs = Directory('assets')
        .listSync(recursive: true)
        .whereType<File>()
        .where((f) => f.path.endsWith('.svg'));
    expect(svgs, isNotEmpty);
    for (final f in svgs) {
      final s = f.readAsStringSync();
      for (final bad in ['<text', '<pattern', '<filter', 'filter=']) {
        expect(s.contains(bad), isFalse, reason: '${f.path} ichida $bad bor');
      }
    }
  });

  testWidgets('brend vidjetlari xatosiz chiziladi', (tester) async {
    await tester.pumpWidget(
      const MaterialApp(
        home: Scaffold(
          body: SingleChildScrollView(
            child: Column(
              children: [
                AuthHeader(),
                ServiceIcon(AppAssets.icTransfer),
                Padding(
                  padding: EdgeInsets.all(16),
                  child: PromoBanner(
                    asset: AppAssets.bannerWelcome,
                    eyebrow: AppBrand.wordmark,
                    title: 'Xush kelibsiz!',
                    subtitle: 'Tez. Oson. Ishonchli.',
                  ),
                ),
              ],
            ),
          ),
        ),
      ),
    );
    await tester.pump(const Duration(milliseconds: 200));
    expect(tester.takeException(), isNull);
    expect(find.text(AppBrand.wordmark), findsWidgets);
    expect(find.text('Xush kelibsiz!'), findsOneWidget);
  });
}
