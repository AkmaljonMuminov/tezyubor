import 'package:flutter_secure_storage/flutter_secure_storage.dart';

/// Tokenlar saqlanadigan joy. Oddiy fayl/SharedPreferences EMAS — faqat Keystore/Keychain (secure storage).
abstract class TokenStore {
  Future<String?> readRefresh();
  Future<String?> readAccess();
  Future<bool> readPinSet();
  Future<void> saveTokens({required String access, required String refresh});
  Future<void> savePinSet(bool value);
  Future<String?> readPhone();
  Future<void> savePhone(String maskedPhone);

  /// Barmoq izi bilan kirish yoqilganmi (faqat shu qurilma sozlamasi; serverga yuborilmaydi).
  Future<bool> readBiometricEnabled();
  Future<void> saveBiometricEnabled(bool value);

  /// Hamma narsani o'chiradi (tokenlar, PIN belgisi, telefon, biometrik sozlama).
  Future<void> clear();
}

class SecureTokenStore implements TokenStore {
  SecureTokenStore([FlutterSecureStorage? storage]) : _s = storage ?? const FlutterSecureStorage();

  final FlutterSecureStorage _s;

  static const _kAccess = 'access_token';
  static const _kRefresh = 'refresh_token';
  static const _kPinSet = 'pin_set';
  static const _kPhone = 'phone_masked';
  static const _kBiometric = 'biometric_enabled';

  @override
  Future<String?> readRefresh() => _s.read(key: _kRefresh);

  @override
  Future<String?> readAccess() => _s.read(key: _kAccess);

  @override
  Future<bool> readPinSet() async => (await _s.read(key: _kPinSet)) == '1';

  @override
  Future<void> saveTokens({required String access, required String refresh}) async {
    await _s.write(key: _kAccess, value: access);
    await _s.write(key: _kRefresh, value: refresh);
  }

  @override
  Future<void> savePinSet(bool value) => _s.write(key: _kPinSet, value: value ? '1' : '0');

  @override
  Future<String?> readPhone() => _s.read(key: _kPhone);

  @override
  Future<void> savePhone(String maskedPhone) => _s.write(key: _kPhone, value: maskedPhone);

  @override
  Future<bool> readBiometricEnabled() async => (await _s.read(key: _kBiometric)) == '1';

  @override
  Future<void> saveBiometricEnabled(bool value) => _s.write(key: _kBiometric, value: value ? '1' : '0');

  @override
  Future<void> clear() async {
    await _s.delete(key: _kAccess);
    await _s.delete(key: _kRefresh);
    await _s.delete(key: _kPinSet);
    await _s.delete(key: _kPhone);
    await _s.delete(key: _kBiometric);
  }
}

/// Testlar uchun xotirada.
class MemoryTokenStore implements TokenStore {
  String? _access;
  String? _refresh;
  bool _pinSet = false;
  String? _phone;
  bool _biometric = false;

  @override
  Future<String?> readRefresh() async => _refresh;

  @override
  Future<String?> readAccess() async => _access;

  @override
  Future<bool> readPinSet() async => _pinSet;

  @override
  Future<void> saveTokens({required String access, required String refresh}) async {
    _access = access;
    _refresh = refresh;
  }

  @override
  Future<void> savePinSet(bool value) async => _pinSet = value;

  @override
  Future<String?> readPhone() async => _phone;

  @override
  Future<void> savePhone(String maskedPhone) async => _phone = maskedPhone;

  @override
  Future<bool> readBiometricEnabled() async => _biometric;

  @override
  Future<void> saveBiometricEnabled(bool value) async => _biometric = value;

  @override
  Future<void> clear() async {
    _access = null;
    _refresh = null;
    _pinSet = false;
    _phone = null;
    _biometric = false;
  }
}
