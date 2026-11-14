import '../../../core/validators.dart';
import 'auth_repository.dart';

/// TEST REJIMI: backend va SMS yo'q. OTP kodi doim [testCode]. Holat faqat xotirada (ilova yopilsa o'chadi).
/// Bu haqiqiy xavfsizlik emas — faqat UI oqimini sinash uchun.
class MockAuthRepository implements AuthRepository {
  static const testCode = '123456';
  static const _maxAttempts = 5;

  final Map<String, int> _attempts = {};
  String? _pin;
  String? _phone;
  bool _biometric = false;

  @override
  Future<String> requestOtp(String phone) async {
    await Future<void>.delayed(const Duration(milliseconds: 400));
    if (normalizePhone(phone) == null) {
      throw const AuthException('VALIDATION_ERROR', "Telefon raqami noto'g'ri");
    }
    _phone = maskPhone(normalizePhone(phone)!);
    final id = 'mock-${DateTime.now().microsecondsSinceEpoch}';
    _attempts[id] = 0;
    return id;
  }

  @override
  Future<void> verifyOtp({required String challengeId, required String code}) async {
    await Future<void>.delayed(const Duration(milliseconds: 300));
    final used = _attempts[challengeId];
    if (used == null) {
      throw const AuthException('OTP_INVALID', "Kod noto'g'ri");
    }
    if (code == testCode) {
      _attempts.remove(challengeId);
      return;
    }
    _attempts[challengeId] = used + 1;
    if (used + 1 >= _maxAttempts) {
      _attempts.remove(challengeId);
      throw const AuthException('OTP_LOCKED', "Urinishlar tugadi. Yangi kod so'rang");
    }
    throw AuthException('OTP_INVALID', "Kod noto'g'ri. Qolgan urinishlar: ${_maxAttempts - used - 1}");
  }

  @override
  Future<bool> hasPin() async => _pin != null;

  @override
  Future<void> createPin(String pin) async {
    if (!isPinAcceptable(pin)) {
      throw const AuthException('PIN_WEAK', 'PIN juda oddiy');
    }
    _pin = pin;
  }

  @override
  Future<bool> verifyPin(String pin) async => _pin != null && _pin == pin;

  @override
  Future<String?> maskedPhone() async => _phone;

  /// Mock'da PIN "server holati" hisoblanadi, shuning uchun chiqishda saqlanib qoladi.
  @override
  Future<void> logout() async {
    _biometric = false; // qurilma sozlamasi: chiqishda o'chadi (Http variantidagidek)
  }

  @override
  Future<bool> biometricEnabled() async => _biometric;

  @override
  Future<void> setBiometricEnabled(bool value) async => _biometric = value;

  /// Mock'da sessiya yangilanadigan server yo'q: PIN o'rnatilgan bo'lsa muvaffaqiyatli.
  @override
  Future<void> refreshSession() async {
    if (_pin == null) throw const AuthException('TOKEN_INVALID', 'Qaytadan kiring');
  }
}
