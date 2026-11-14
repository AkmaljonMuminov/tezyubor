import 'dart:async';
import 'dart:convert';

import 'package:http/http.dart' as http;

/// Server xatosi (`{"error": {"code", "message", ...}}`) yoki tarmoq xatosi (`code == 'NETWORK'`).
class ApiException implements Exception {
  const ApiException({required this.status, required this.code, required this.message, this.details});

  final int status;
  final String code;
  final String message;
  final Map<String, dynamic>? details;

  bool get isNetwork => code == 'NETWORK';

  @override
  String toString() => 'ApiException($status, $code)';
}

/// Yagona HTTP klient: JSON, timeout, xatolarni [ApiException] ga o'giradi.
/// Maxfiy qiymatlar (token, PIN) hech qachon log'ga yozilmaydi.
class ApiClient {
  ApiClient({
    required this.baseUrl,
    http.Client? client,
    this.timeout = const Duration(seconds: 15),
  }) : _client = client ?? http.Client();

  final String baseUrl;
  final Duration timeout;
  final http.Client _client;

  /// POST. Javob tanasi bo'sh bo'lsa (204) `null` qaytadi. [headers] — qo'shimcha sarlavhalar (masalan `Idempotency-Key`).
  Future<Map<String, dynamic>?> post(
    String path, {
    Map<String, dynamic>? body,
    String? bearer,
    Map<String, String>? headers,
  }) =>
      _send('POST', path, body: body ?? const <String, dynamic>{}, bearer: bearer, headers: headers);

  Future<Map<String, dynamic>?> get(
    String path, {
    String? bearer,
    Map<String, String>? query,
    Map<String, String>? headers,
  }) =>
      _send('GET', path, bearer: bearer, query: query, headers: headers);

  Future<Map<String, dynamic>?> delete(String path, {String? bearer, Map<String, String>? headers}) =>
      _send('DELETE', path, bearer: bearer, headers: headers);

  Future<Map<String, dynamic>?> _send(
    String method,
    String path, {
    Map<String, dynamic>? body,
    String? bearer,
    Map<String, String>? query,
    Map<String, String>? headers,
  }) async {
    var uri = Uri.parse('$baseUrl$path');
    if (query != null && query.isNotEmpty) uri = uri.replace(queryParameters: query);
    final allHeaders = <String, String>{
      'Accept': 'application/json',
      if (body != null) 'Content-Type': 'application/json',
      if (bearer != null) 'Authorization': 'Bearer $bearer',
      ...?headers,
    };

    http.Response res;
    try {
      final Future<http.Response> call;
      switch (method) {
        case 'GET':
          call = _client.get(uri, headers: allHeaders);
        case 'DELETE':
          call = _client.delete(uri, headers: allHeaders);
        default:
          call = _client.post(uri, headers: allHeaders, body: jsonEncode(body ?? const <String, dynamic>{}));
      }
      res = await call.timeout(timeout);
    } on TimeoutException {
      throw const ApiException(status: 0, code: 'NETWORK', message: "Server javob bermadi. Qayta urinib ko'ring");
    } on http.ClientException {
      throw const ApiException(status: 0, code: 'NETWORK', message: "Internetga ulanib bo'lmadi");
    }

    final text = utf8.decode(res.bodyBytes);
    Map<String, dynamic>? json;
    if (text.isNotEmpty) {
      try {
        final decoded = jsonDecode(text);
        if (decoded is Map<String, dynamic>) json = decoded;
      } on FormatException {
        json = null;
      }
    }

    if (res.statusCode >= 200 && res.statusCode < 300) return json;

    final err = json?['error'];
    if (err is Map<String, dynamic>) {
      final details = Map<String, dynamic>.from(err)
        ..remove('code')
        ..remove('message');
      throw ApiException(
        status: res.statusCode,
        code: (err['code'] as String?) ?? 'APP_ERROR',
        message: (err['message'] as String?) ?? 'Xatolik yuz berdi',
        details: details.isEmpty ? null : details,
      );
    }
    // FastAPI'ning o'z validatsiya xatosi (422) yoki kutilmagan javob.
    throw ApiException(
      status: res.statusCode,
      code: res.statusCode == 422 ? 'VALIDATION_ERROR' : 'SERVER_ERROR',
      message: res.statusCode == 422 ? "Ma'lumot noto'g'ri" : 'Xatolik yuz berdi',
    );
  }
}
