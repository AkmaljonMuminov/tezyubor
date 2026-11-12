import 'package:flutter_riverpod/flutter_riverpod.dart';

import '../../../core/brand.dart';
import '../../../core/network/api_client.dart';
import '../../../core/network/token_store.dart';
import 'http_auth_repository.dart';
import 'mock_auth_repository.dart';

class AuthException implements Exception {
  const AuthException(this.code, this.message);
  final String code;
  final String message;

  @override
  String toString() => 'AuthException($code)';
}

/// Autentifikatsiya shartnomasi. `API_MODE=mock` da `MockAuthRepository`,
/// `API_MODE=real` da backend (`/v1/auth/*`) bilan ishlovchi `HttpAuthRepository`.
abstract class AuthRepository {
  /// OTP so'raydi, `challengeId` qaytaradi.
  Future<String> requestOtp(String phone);

  /// Kod noto'g'ri/muddati o'tgan bo'lsa [AuthException] tashlaydi.
  Future<void> verifyOtp({required String challengeId, required String code});

  Future<bool> hasPin();
  Future<void> createPin(String pin);

  /// `true` — to'g'ri, `false` — noto'g'ri. Bloklangan yoki tarmoq xatosida [AuthException].
  Future<bool> verifyPin(String pin);

  /// Oxirgi kirgan telefon (maskalangan), yo'q bo'lsa `null`.
  Future<String?> maskedPhone();

  /// Qurilmadagi sessiyani tugatadi. Serverda tokenni bekor qilish endpointi hali yo'q.
  Future<void> logout();
}

final authRepositoryProvider = Provider<AuthRepository>((ref) {
  if (kMockMode) return MockAuthRepository();
  return HttpAuthRepository(ApiClient(baseUrl: kApiBaseUrl), SecureTokenStore());
});
