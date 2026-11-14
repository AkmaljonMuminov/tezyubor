import 'dart:io';

import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:go_router/go_router.dart';
import 'package:tezyubor_mobile/core/assets.dart';
import 'package:tezyubor_mobile/core/brand.dart';
import 'package:tezyubor_mobile/core/router.dart';
import 'package:tezyubor_mobile/features/auth/data/auth_repository.dart';
import 'package:tezyubor_mobile/features/auth/data/mock_auth_repository.dart';
import 'package:tezyubor_mobile/features/splash/splash_screen.dart';

/// ORVEX PAY brendlash: foydalanuvchiga ko'rinadigan nomlar yangilangan, texnik identifikatorlar O'ZGARMAGAN.
void main() {
  test('brend nomi, wordmark va shior ORVEX PAY', () {
    expect(AppBrand.name, 'ORVEX PAY');
    expect(AppBrand.wordmark, 'ORVEX PAY');
    expect(AppBrand.slogan, 'TEZ • XAVFSIZ • QULAY');
  });

  test("applicationId o'zgarmagan (brend almashganda paket nomiga tegilmaydi)", () {
    expect(AppBrand.appId, 'uz.tezyubor.app');
  });

  test("foydalanuvchi matnlarida eski brend nomi qolmagan (brand.dart va strings.dart)", () {
    final brand = File('lib/core/brand.dart').readAsStringSync();
    // appId texnik identifikator — istisno; qolgan hamma joyda eski nom bo'lmasligi kerak.
    final brandWithoutAppId = brand.split('\n').where((l) => !l.contains('uz.tezyubor.app')).join('\n');
    expect(brandWithoutAppId.toLowerCase().contains('tezyubor'), isFalse);
    expect(File('lib/core/l10n/strings.dart').readAsStringSync().toLowerCase().contains('tezyubor'), isFalse);
  });

  test("brend resurslari mavjud va logo.png haqiqiy 512x512 PNG", () {
    for (final p in [AppAssets.logo, AppAssets.splashBg]) {
      expect(File(p).existsSync(), isTrue, reason: p);
    }
    final bytes = File(AppAssets.logo).readAsBytesSync();
    expect(bytes.sublist(0, 8), [0x89, 0x50, 0x4E, 0x47, 0x0D, 0x0A, 0x1A, 0x0A], reason: 'PNG imzosi');
    final data = ByteData.sublistView(bytes);
    expect(data.getUint32(16), 512, reason: 'kenglik');
    expect(data.getUint32(20), 512, reason: 'balandlik');
  });

  test("launcher resurslari to'liq: har zichlikda 3 ta PNG + adaptive XML + native splash", () {
    for (final d in ['mdpi', 'hdpi', 'xhdpi', 'xxhdpi', 'xxxhdpi']) {
      for (final n in ['ic_launcher', 'ic_launcher_background', 'ic_launcher_foreground']) {
        expect(File('launcher_res/mipmap-$d/$n.png').existsSync(), isTrue, reason: '$d/$n');
      }
    }
    expect(File('launcher_res/mipmap-anydpi-v26/ic_launcher.xml').existsSync(), isTrue);
    expect(File('launcher_res/drawable-nodpi/launch_logo.png').existsSync(), isTrue);
    expect(File('launcher_res/drawable/launch_background.xml').readAsStringSync(), contains('@drawable/launch_logo'));
    expect(File('launcher_res/values/orvex_colors.xml').readAsStringSync(), contains('#06143A'));
  });

  testWidgets("splash ORVEX PAY nomi va shiorini ko'rsatadi, so'ng PIN/telefon ekraniga o'tadi", (tester) async {
    tester.view.physicalSize = const Size(1080, 2400);
    tester.view.devicePixelRatio = 2.0;
    addTearDown(tester.view.reset);

    final router = GoRouter(
      initialLocation: Routes.splash,
      routes: [
        GoRoute(path: Routes.splash, builder: (_, __) => const SplashScreen()),
        GoRoute(path: Routes.phone, builder: (_, __) => const Scaffold(body: Text('PHONE'))),
        GoRoute(path: Routes.pinLogin, builder: (_, __) => const Scaffold(body: Text('PIN'))),
      ],
    );
    await tester.pumpWidget(
      ProviderScope(
        overrides: [authRepositoryProvider.overrideWithValue(MockAuthRepository())],
        child: MaterialApp.router(routerConfig: router),
      ),
    );
    await tester.pump(const Duration(milliseconds: 100));
    expect(tester.takeException(), isNull);
    expect(find.text('ORVEX PAY'), findsOneWidget);
    expect(find.text('TEZ • XAVFSIZ • QULAY'), findsOneWidget);
    expect(find.textContaining('TEZYUBOR'), findsNothing);

    await tester.pump(const Duration(milliseconds: 1300));
    await tester.pumpAndSettle();
    expect(find.text('PHONE'), findsOneWidget); // PIN o'rnatilmagan — telefon ekraniga (mavjud mantiq o'zgarmagan)
  });
}
