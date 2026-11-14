import 'dart:convert';

import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:go_router/go_router.dart';
import 'package:http/http.dart' as http;
import 'package:http/testing.dart';
import 'package:tezyubor_mobile/core/l10n/strings.dart';
import 'package:tezyubor_mobile/core/network/api_client.dart';
import 'package:tezyubor_mobile/core/network/token_store.dart';
import 'package:tezyubor_mobile/core/router.dart';
import 'package:tezyubor_mobile/core/security/biometric_service.dart';
import 'package:tezyubor_mobile/features/auth/data/auth_repository.dart';
import 'package:tezyubor_mobile/features/auth/data/http_auth_repository.dart';
import 'package:tezyubor_mobile/features/auth/data/mock_auth_repository.dart';
import 'package:tezyubor_mobile/features/auth/presentation/pin_login_screen.dart';

http.Response _json(int status, Object body) => http.Response(
      jsonEncode(body),
      status,
      headers: {'content-type': 'application/json; charset=utf-8'},
    );

class _GoneSessionRepo extends MockAuthRepository {
  @override
  Future<void> refreshSession() async => throw const AuthException('TOKEN_INVALID', 'Qaytadan kiring');
}

void main() {
  TestWidgetsFlutterBinding.ensureInitialized(); // plagin kanali yo'q — MissingPluginException deterministik

  group('LocalAuthBiometricService: plagin yo\'q/xato bo\'lsa yiqilmaydi', () {
    test('holat `available` emas, tasdiq `false`', () async {
      final service = LocalAuthBiometricService();
      expect(await service.status(), isNot(BiometricStatus.available));
      expect(await service.authenticate(reason: 'test'), isFalse);
    });
  });

  group('HttpAuthRepository: logout va sessiyani yangilash', () {
    late MemoryTokenStore tokens;
    setUp(() async {
      tokens = MemoryTokenStore();
      await tokens.saveTokens(access: 'A1', refresh: 'R1');
      await tokens.savePinSet(true);
      await tokens.saveBiometricEnabled(true);
    });

    HttpAuthRepository repoWith(MockClient client) => HttpAuthRepository(
          ApiClient(baseUrl: 'http://test', client: client),
          tokens,
          deviceLabel: 'Test qurilma',
        );

    test('logout serverga refresh token yuboradi va qurilmani to\'liq tozalaydi', () async {
      final calls = <String>[];
      final repo = repoWith(MockClient((req) async {
        calls.add(req.url.path);
        expect(jsonDecode(req.body), {'refresh_token': 'R1'});
        return http.Response('', 204);
      }));
      await repo.logout();
      expect(calls, ['/v1/auth/logout']);
      expect(await tokens.readRefresh(), isNull);
      expect(await tokens.readAccess(), isNull);
      expect(await tokens.readBiometricEnabled(), isFalse);
      expect(await repo.hasPin(), isFalse);
    });

    test('server javob bermasa ham logout qurilmani tozalaydi', () async {
      final repo = repoWith(MockClient((_) async => throw http.ClientException('offline')));
      await repo.logout();
      expect(await tokens.readRefresh(), isNull);
    });

    test('server 500 qaytarsa ham logout qurilmani tozalaydi', () async {
      final repo = repoWith(MockClient((_) async => _json(500, {'x': 1})));
      await repo.logout();
      expect(await tokens.readRefresh(), isNull);
    });

    test('token yo\'q bo\'lsa serverga murojaat qilinmaydi', () async {
      await tokens.clear();
      var called = false;
      final repo = repoWith(MockClient((_) async {
        called = true;
        return http.Response('', 204);
      }));
      await repo.logout();
      expect(called, isFalse);
    });

    test('OTP tasdiqlashda qurilma nomi yuboriladi (model/identifikator emas)', () async {
      late Map<String, dynamic> body;
      final repo = repoWith(MockClient((req) async {
        body = jsonDecode(req.body) as Map<String, dynamic>;
        return _json(200, {'access_token': 'A', 'refresh_token': 'R', 'pin_set': false});
      }));
      await repo.verifyOtp(challengeId: 'c1', code: '123456');
      expect(body['device_label'], 'Test qurilma');
      expect(body.keys.toSet(), {'challenge_id', 'code', 'device_label'});
    });

    test('refreshSession: yangi tokenlar saqlanadi', () async {
      final repo = repoWith(MockClient((req) async {
        expect(req.url.path, '/v1/auth/token/refresh');
        expect(jsonDecode(req.body), {'refresh_token': 'R1'});
        return _json(200, {'access_token': 'A2', 'refresh_token': 'R2'});
      }));
      await repo.refreshSession();
      expect(await tokens.readAccess(), 'A2');
      expect(await tokens.readRefresh(), 'R2');
    });

    test('refreshSession: bekor qilingan/qayta ishlatilgan sessiya — tozalanadi va AuthException', () async {
      for (final code in ['TOKEN_INVALID', 'TOKEN_REUSE_DETECTED']) {
        await tokens.saveTokens(access: 'A1', refresh: 'R1');
        final repo = repoWith(MockClient((_) async => _json(401, {
              'error': {'code': code, 'message': 'x'},
            })));
        await expectLater(repo.refreshSession(), throwsA(isA<AuthException>().having((e) => e.code, 'code', code)));
        expect(await tokens.readRefresh(), isNull, reason: code);
      }
    });

    test('refreshSession: tarmoq xatosida tokenlar saqlanib qoladi', () async {
      final repo = repoWith(MockClient((_) async => throw http.ClientException('offline')));
      await expectLater(repo.refreshSession(), throwsA(isA<AuthException>().having((e) => e.code, 'code', 'NETWORK')));
      expect(await tokens.readRefresh(), 'R1');
    });

    test('biometrik sozlama saqlanadi va o\'qiladi', () async {
      final repo = repoWith(MockClient((_) async => http.Response('', 204)));
      await repo.setBiometricEnabled(false);
      expect(await repo.biometricEnabled(), isFalse);
      await repo.setBiometricEnabled(true);
      expect(await repo.biometricEnabled(), isTrue);
    });
  });

  group('PinLoginScreen: barmoq izi va PIN zaxirasi', () {
    Future<(MockAuthRepository, FakeBiometricService)> pump(
      WidgetTester tester, {
      MockAuthRepository? repo,
      FakeBiometricService? bio,
      bool enabled = true,
    }) async {
      tester.view.physicalSize = const Size(1080, 2400);
      tester.view.devicePixelRatio = 2.0;
      addTearDown(tester.view.reset);

      final auth = repo ?? MockAuthRepository();
      await auth.createPin('2580');
      await auth.setBiometricEnabled(enabled);
      final fake = bio ?? FakeBiometricService();

      final router = GoRouter(
        initialLocation: Routes.pinLogin,
        routes: [
          GoRoute(path: Routes.pinLogin, builder: (_, __) => const PinLoginScreen()),
          GoRoute(path: Routes.home, builder: (_, __) => const Scaffold(body: Text('HOME'))),
          GoRoute(path: Routes.phone, builder: (_, __) => const Scaffold(body: Text('PHONE'))),
        ],
      );
      await tester.pumpWidget(
        ProviderScope(
          key: UniqueKey(),
          overrides: [
            authRepositoryProvider.overrideWithValue(auth),
            biometricServiceProvider.overrideWithValue(fake),
          ],
          child: MaterialApp.router(routerConfig: router),
        ),
      );
      await tester.pumpAndSettle();
      return (auth, fake);
    }

    Future<void> enterPin(WidgetTester tester, String pin) async {
      for (final d in pin.split('')) {
        await tester.tap(find.text(d));
        await tester.pump();
      }
      await tester.pumpAndSettle();
    }

    testWidgets('yoqilgan + mavjud + muvaffaqiyatli: PIN so\'ramay bosh sahifaga o\'tadi', (tester) async {
      final (_, bio) = await pump(tester);
      expect(bio.authenticateCalls, 1);
      expect(find.text('HOME'), findsOneWidget);
    });

    testWidgets('biometrika bekor qilindi: PIN ekrani qoladi, tugma ko\'rinadi, PIN bilan kirish ishlaydi', (tester) async {
      final (_, bio) = await pump(tester, bio: FakeBiometricService(succeeds: false));
      expect(find.text('HOME'), findsNothing);
      expect(find.byKey(const Key('biometric-login')), findsOneWidget);
      expect(bio.authenticateCalls, 1);

      await enterPin(tester, '2580');
      expect(find.text('HOME'), findsOneWidget);
    });

    testWidgets('noto\'g\'ri PIN: xato ko\'rsatiladi, biometrika bilan baribir kirish mumkin', (tester) async {
      final (_, bio) = await pump(tester, bio: FakeBiometricService(succeeds: false));
      await enterPin(tester, '9999');
      expect(find.text(Strings.pinWrong), findsOneWidget);
      bio.succeeds = true;
      await tester.tap(find.byKey(const Key('biometric-login')));
      await tester.pumpAndSettle();
      expect(find.text('HOME'), findsOneWidget);
    });

    testWidgets('sessiya bekor qilingan: biometrika o\'tsa ham telefon ekraniga qaytaradi', (tester) async {
      await pump(tester, repo: _GoneSessionRepo());
      expect(find.text('PHONE'), findsOneWidget);
      expect(find.text('HOME'), findsNothing);
    });

    testWidgets('sozlama o\'chiq: tugma yo\'q, biometrika so\'ralmaydi', (tester) async {
      final (_, bio) = await pump(tester, enabled: false);
      expect(bio.authenticateCalls, 0);
      expect(find.byKey(const Key('biometric-login')), findsNothing);
      expect(find.text('HOME'), findsNothing);
    });

    testWidgets('barmoq izi yozilmagan/mavjud emas: PIN bilan kiriladi, biometrika so\'ralmaydi', (tester) async {
      for (final st in [BiometricStatus.notEnrolled, BiometricStatus.notSupported, BiometricStatus.unavailable]) {
        final (_, bio) = await pump(tester, bio: FakeBiometricService(fakeStatus: st));
        expect(bio.authenticateCalls, 0, reason: '$st');
        expect(find.byKey(const Key('biometric-login')), findsNothing, reason: '$st');
        await enterPin(tester, '2580');
        expect(find.text('HOME'), findsOneWidget, reason: '$st');
      }
    });
  });
}
