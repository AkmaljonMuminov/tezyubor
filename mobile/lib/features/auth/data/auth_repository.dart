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

  /// Sessiyani tugatadi: serverda refresh tokenni bekor qilishga urinadi (internet bo'lmasa ham davom etadi)
  /// va qurilmadagi hamma narsani o'chiradi.
  Future<void> logout();

  /// Barmoq izi bilan kirish shu qurilmada yoqilganmi.
  Future<bool> biometricEnabled();
  Future<void> setBiometricEnabled(bool value);

  /// Biometrik tasdiqdan KEYIN chaqiriladi: saqlangan refresh token bilan sessiyani yangilaydi (PIN so'ralmaydi).
  /// Sessiya yaroqsiz/bekor qilingan bo'lsa tokenlar o'chiriladi va [AuthException] (`TOKEN_INVALID`) tashlanadi.
  /// Eslatma: pul harakati baribir serverda PIN bilan tasdiqlanadi — biometrika uni almashtirmaydi.
  Future<void> refreshSession();
}

final authRepositoryProvider = Provider<AuthRepository>((ref) {
  if (kMockMode) return MockAuthRepository();
  return HttpAuthRepository(ApiClient(baseUrl: kApiBaseUrl), SecureTokenStore());
});
