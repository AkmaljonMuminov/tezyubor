import 'dart:async';

import 'api_client.dart';
import 'token_store.dart';

/// Access token talab qiladigan so'rovlar uchun klient.
///
/// Access token eskirsa (401 `TOKEN_INVALID`) refresh token bilan YANGILAYDI va so'rovni BIR marta takrorlaydi.
/// Bir vaqtda ko'p so'rov 401 olsa ham yangilash BITTA bo'ladi (single-flight): refresh token aylanuvchi bo'lgani uchun
/// parallel yangilash serverda "qayta ishlatish" deb baholanib, sessiyani o'ldirib qo'yar edi (AnorBank `TokenAuthenticator` xatosi).
/// Yangilash muvaffaqiyatsiz bo'lib, sessiya yaroqsiz bo'lsa — qurilmadagi tokenlar o'chiriladi va [ApiException] tashlanadi.
class AuthedApiClient {
  AuthedApiClient(this._api, this._tokens);

  final ApiClient _api;
  final TokenStore _tokens;
  Future<void>? _refreshing;

  static const _sessionGone = ApiException(status: 401, code: 'TOKEN_INVALID', message: 'Qaytadan kiring');

  Future<Map<String, dynamic>?> get(String path, {Map<String, String>? query}) =>
      _authed((bearer) => _api.get(path, bearer: bearer, query: query));

  Future<Map<String, dynamic>?> delete(String path) => _authed((bearer) => _api.delete(path, bearer: bearer));

  Future<Map<String, dynamic>?> post(
    String path, {
    Map<String, dynamic>? body,
    Map<String, String>? headers,
  }) =>
      _authed((bearer) => _api.post(path, body: body, bearer: bearer, headers: headers));

  Future<Map<String, dynamic>?> _authed(Future<Map<String, dynamic>?> Function(String bearer) call) async {
    final access = await _tokens.readAccess();
    if (access == null) throw _sessionGone;
    try {
      return await call(access);
    } on ApiException catch (e) {
      if (e.code != 'TOKEN_INVALID') rethrow;
    }
    // Access token yaroqsiz: yangilaymiz (bir vaqtda faqat bitta) va faqat BIR marta takrorlaymiz — cheksiz sikl yo'q.
    await _refreshOnce(access);
    final fresh = await _tokens.readAccess();
    if (fresh == null) throw _sessionGone;
    return call(fresh);
  }

  Future<void> _refreshOnce(String staleAccess) {
    final running = _refreshing;
    if (running != null) return running;
    final started = _refresh(staleAccess).whenComplete(() => _refreshing = null);
    _refreshing = started;
    return started;
  }

  Future<void> _refresh(String staleAccess) async {
    // Kutish paytida boshqa so'rov allaqachon yangilab qo'ygan bo'lishi mumkin — qayta yangilamaymiz.
    final current = await _tokens.readAccess();
    if (current != null && current != staleAccess) return;

    final refresh = await _tokens.readRefresh();
    if (refresh == null) {
      await _tokens.clear();
      throw _sessionGone;
    }
    try {
      final res = await _api.post('/v1/auth/token/refresh', body: {'refresh_token': refresh});
      final access = res?['access_token'];
      final newRefresh = res?['refresh_token'];
      if (access is! String || newRefresh is! String) {
        throw const ApiException(status: 500, code: 'SERVER_ERROR', message: "Server javobi noto'g'ri");
      }
      await _tokens.saveTokens(access: access, refresh: newRefresh);
    } on ApiException catch (e) {
      if (e.code == 'TOKEN_INVALID' || e.code == 'TOKEN_REUSE_DETECTED') {
        await _tokens.clear(); // sessiya tugagan yoki bekor qilingan: qayta OTP bilan kirish kerak
      }
      rethrow;
    }
  }
}
