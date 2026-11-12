import 'dart:convert';

import 'package:flutter_test/flutter_test.dart';
import 'package:http/http.dart' as http;
import 'package:http/testing.dart';
import 'package:tezyubor_mobile/core/network/api_client.dart';
import 'package:tezyubor_mobile/core/network/token_store.dart';
import 'package:tezyubor_mobile/features/auth/data/auth_repository.dart';
import 'package:tezyubor_mobile/features/auth/data/http_auth_repository.dart';

http.Response _json(int status, Object body) => http.Response(
      jsonEncode(body),
      status,
      headers: {'content-type': 'application/json; charset=utf-8'},
    );

void main() {
  late MemoryTokenStore tokens;

  HttpAuthRepository repoWith(MockClient client) =>
      HttpAuthRepository(ApiClient(baseUrl: 'http://test', client: client), tokens);

  setUp(() => tokens = MemoryTokenStore());

  test('OTP oqimi: so\'rov, tasdiqlash, tokenlar saqlanadi', () async {
    final client = MockClient((req) async {
      if (req.url.path == '/v1/auth/otp/request') {
        expect(jsonDecode(req.body), {'phone': '998901234567'});
        return _json(200, {'challenge_id': 'c1', 'expires_in': 120});
      }
      if (req.url.path == '/v1/auth/otp/verify') {
        return _json(200, {
          'access_token': 'A1',
          'refresh_token': 'R1',
          'token_type': 'bearer',
          'expires_in': 600,
          'pin_set': false,
        });
      }
      return _json(404, {});
    });
    final repo = repoWith(client);

    expect(await repo.requestOtp('90 123 45 67'), 'c1');
    await repo.verifyOtp(challengeId: 'c1', code: '123456');
    expect(await tokens.readAccess(), 'A1');
    expect(await tokens.readRefresh(), 'R1');
    expect(await repo.hasPin(), isFalse);
  });

  test('PIN o\'rnatish Bearer token bilan yuboriladi', () async {
    await tokens.saveTokens(access: 'A1', refresh: 'R1');
    final client = MockClient((req) async {
      expect(req.url.path, '/v1/auth/pin/set');
      expect(req.headers['Authorization'], 'Bearer A1');
      return http.Response('', 204);
    });
    final repo = repoWith(client);
    await repo.createPin('2580');
    expect(await repo.hasPin(), isTrue);
  });

  test("PIN login: noto'g'ri PIN -> false, bloklangan -> AuthException", () async {
    await tokens.saveTokens(access: 'A1', refresh: 'R1');
    await tokens.savePinSet(true);
    var call = 0;
    final client = MockClient((req) async {
      call++;
      if (call == 1) {
        return _json(401, {
          'error': {'code': 'PIN_INVALID', 'message': "PIN noto'g'ri"},
        });
      }
      return _json(423, {
        'error': {'code': 'PIN_LOCKED', 'message': 'blok', 'retry_after': 600},
      });
    });
    final repo = repoWith(client);

    expect(await repo.verifyPin('2580'), isFalse);
    await expectLater(
      repo.verifyPin('2580'),
      throwsA(isA<AuthException>().having((e) => e.code, 'code', 'PIN_LOCKED')),
    );
  });

  test('refresh token yaroqsiz bo\'lsa qurilmadan tozalanadi', () async {
    await tokens.saveTokens(access: 'A1', refresh: 'R1');
    await tokens.savePinSet(true);
    final client = MockClient((_) async => _json(401, {
          'error': {'code': 'TOKEN_REUSE_DETECTED', 'message': 'x'},
        }));
    final repo = repoWith(client);

    await expectLater(repo.verifyPin('2580'), throwsA(isA<AuthException>()));
    expect(await tokens.readRefresh(), isNull);
    expect(await repo.hasPin(), isFalse);
  });

  test('tarmoq xatosi NETWORK kodi bilan qaytadi', () async {
    final client = MockClient((_) async => throw http.ClientException('offline'));
    final api = ApiClient(baseUrl: 'http://test', client: client);
    await expectLater(
      api.post('/v1/auth/otp/request', body: {'phone': '998901234567'}),
      throwsA(isA<ApiException>().having((e) => e.isNetwork, 'isNetwork', isTrue)),
    );
  });
}
