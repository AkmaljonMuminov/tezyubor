import 'package:flutter_riverpod/flutter_riverpod.dart';

import '../../../core/brand.dart';
import 'mock_auth_repository.dart';

class AuthException implements Exception {
  const AuthException(this.code, this.message);
  final String code;
  final String message;

  @override
  String toString() => 'AuthException($code)';
}

/// Autentifikatsiya shartnomasi. Hozir faqat `MockAuthRepository` bor;
/// 2-bosqichda backend (`/v1/auth/*`) bilan ishlovchi HTTP implementatsiya qo'shiladi.
abstract class AuthRepository {
  /// OTP so'raydi, `challengeId` qaytaradi.
  Future<String> requestOtp(String phone);

  /// Kod noto'g'ri/muddati o'tgan bo'lsa [AuthException] tashlaydi.
  Future<void> verifyOtp({required String challengeId, required String code});

  Future<bool> hasPin();
  Future<void> createPin(String pin);
  Future<bool> verifyPin(String pin);
}

final authRepositoryProvider = Provider<AuthRepository>((ref) {
  if (!kMockMode) {
    throw UnimplementedError("HTTP AuthRepository hali yozilmagan (2-bosqich). API_MODE=mock ishlating.");
  }
  return MockAuthRepository();
});
