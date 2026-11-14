import 'dart:convert';

import 'package:flutter_test/flutter_test.dart';
import 'package:http/http.dart' as http;
import 'package:http/testing.dart';
import 'package:tezyubor_mobile/core/network/api_client.dart';
import 'package:tezyubor_mobile/core/network/authed_api.dart';
import 'package:tezyubor_mobile/core/network/token_store.dart';

http.Response _json(int status, Object body) => http.Response(
      jsonEncode(body),
      status,
      headers: {'content-type': 'application/json; charset=utf-8'},
    );

http.Response _tokenInvalid() => _json(401, {
      'error': {'code': 'TOKEN_INVALID', 'message': 'Token yaroqsiz'},
    });

/// Server simulyatori: faqat `Bearer NEW` qabul qilinadi; `/token/refresh` OLD refresh'ni NEW ga almashtiradi.
class _Server {
  int refreshCalls = 0;
  int dataCalls = 0;
  final bearers = <String?>[];
  Object refreshResult = {'access_token': 'NEW', 'refresh_token': 'R2'};
  int refreshStatus = 200;

  Future<http.Response> handle(http.Request req) async {
    if (req.url.path == '/v1/auth/token/refresh') {
      refreshCalls++;
      await Future<void>.delayed(const Duration(milliseconds: 20)); // parallel so'rovlar ustma-ust tushsin
      return _json(refreshStatus, refreshResult);
    }
    dataCalls++;
    bearers.add(req.headers['Authorization']);
    if (req.url.path == '/v1/wallet/fail') {
      return _json(409, {
        'error': {'code': 'INSUFFICIENT_FUNDS', 'message': 'yetarli emas'},
      });
    }
    if (req.headers['Authorization'] == 'Bearer NEW') return _json(200, {'ok': true});
    return _tokenInvalid();
  }
}

void main() {
  late MemoryTokenStore tokens;
  late _Server server;
  late AuthedApiClient api;

  setUp(() async {
    tokens = MemoryTokenStore();
    await tokens.saveTokens(access: 'OLD', refresh: 'R1');
    server = _Server();
    api = AuthedApiClient(ApiClient(baseUrl: 'http://test', client: MockClient(server.handle)), tokens);
  });

  test('access eskirgan: yangilanadi va so\'rov bir marta takrorlanadi', () async {
    final res = await api.get('/v1/wallet/cards');
    expect(res, {'ok': true});
    expect(server.refreshCalls, 1);
    expect(server.bearers, ['Bearer OLD', 'Bearer NEW']);
    expect(await tokens.readAccess(), 'NEW');
    expect(await tokens.readRefresh(), 'R2');
  });

  test('parallel 6 ta so\'rov: yangilash FAQAT BITTA (refresh token aylanuvchi)', () async {
    final results = await Future.wait([for (var i = 0; i < 6; i++) api.get('/v1/wallet/cards')]);
    expect(results.every((r) => r?['ok'] == true), isTrue);
    expect(server.refreshCalls, 1);
  });

  test('yaroqli access bo\'lsa yangilash so\'ralmaydi', () async {
    await tokens.saveTokens(access: 'NEW', refresh: 'R1');
    await api.get('/v1/wallet/cards');
    expect(server.refreshCalls, 0);
    expect(server.dataCalls, 1);
  });

  test('refresh muvaffaqiyatsiz (sessiya tugagan): tokenlar tozalanadi, xato tashlanadi', () async {
    for (final code in ['TOKEN_INVALID', 'TOKEN_REUSE_DETECTED']) {
      await tokens.saveTokens(access: 'OLD', refresh: 'R1');
      server.refreshStatus = 401;
      server.refreshResult = {
        'error': {'code': code, 'message': 'x'},
      };
      await expectLater(
        api.get('/v1/wallet/cards'),
        throwsA(isA<ApiException>().having((e) => e.code, 'code', code)),
      );
      expect(await tokens.readRefresh(), isNull, reason: code);
      expect(await tokens.readAccess(), isNull, reason: code);
    }
  });

  test('tarmoq xatosida yangilash vaqtida tokenlar O\'CHIRILMAYDI (vaqtinchalik muammo)', () async {
    final offline = AuthedApiClient(
      ApiClient(
        baseUrl: 'http://test',
        client: MockClient((req) async {
          if (req.url.path == '/v1/auth/token/refresh') throw http.ClientException('offline');
          return _tokenInvalid();
        }),
      ),
      tokens,
    );
    await expectLater(offline.get('/x'), throwsA(isA<ApiException>().having((e) => e.isNetwork, 'isNetwork', isTrue)));
    expect(await tokens.readRefresh(), 'R1');
  });

  test('takrorlangan so\'rov ham 401 bo\'lsa — cheksiz sikl yo\'q, aynan 2 ta so\'rov', () async {
    server.refreshResult = {'access_token': 'STILL_BAD', 'refresh_token': 'R2'};
    await expectLater(
      api.get('/v1/wallet/cards'),
      throwsA(isA<ApiException>().having((e) => e.code, 'code', 'TOKEN_INVALID')),
    );
    expect(server.dataCalls, 2);
    expect(server.refreshCalls, 1);
  });

  test('boshqa xatolar yangilashni boshlamaydi', () async {
    await expectLater(
      api.post('/v1/wallet/fail', body: {}),
      throwsA(isA<ApiException>().having((e) => e.code, 'code', 'INSUFFICIENT_FUNDS')),
    );
    expect(server.refreshCalls, 0);
    expect(server.dataCalls, 1);
  });

  test('token umuman yo\'q: tarmoqqa chiqmasdan TOKEN_INVALID', () async {
    await tokens.clear();
    await expectLater(
      api.get('/v1/wallet/cards'),
      throwsA(isA<ApiException>().having((e) => e.code, 'code', 'TOKEN_INVALID')),
    );
    expect(server.dataCalls, 0);
    expect(server.refreshCalls, 0);
  });

  test('POST: Idempotency-Key va Bearer sarlavhalari yuboriladi', () async {
    await tokens.saveTokens(access: 'NEW', refresh: 'R1');
    late http.Request seen;
    final a = AuthedApiClient(
      ApiClient(
        baseUrl: 'http://test',
        client: MockClient((req) async {
          seen = req;
          return _json(200, {'ok': true});
        }),
      ),
      tokens,
    );
    await a.post('/v1/wallet/transfers', body: {'amount_tiyin': 100000}, headers: {'Idempotency-Key': 'key-00000001'});
    expect(seen.headers['Idempotency-Key'], 'key-00000001');
    expect(seen.headers['Authorization'], 'Bearer NEW');
    expect(jsonDecode(seen.body), {'amount_tiyin': 100000});
  });

  test('GET: query parametrlari URL\'ga qo\'shiladi, tana va Content-Type yo\'q', () async {
    await tokens.saveTokens(access: 'NEW', refresh: 'R1');
    late http.Request seen;
    final a = AuthedApiClient(
      ApiClient(
        baseUrl: 'http://test',
        client: MockClient((req) async {
          seen = req;
          return _json(200, {'ok': true});
        }),
      ),
      tokens,
    );
    await a.get('/v1/wallet/transactions', query: {'limit': '20', 'status': 'completed'});
    expect(seen.url.queryParameters, {'limit': '20', 'status': 'completed'});
    expect(seen.headers.containsKey('Content-Type'), isFalse);
  });
}
