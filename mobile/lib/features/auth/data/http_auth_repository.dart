import '../../../core/network/api_client.dart';
import '../../../core/network/token_store.dart';
import '../../../core/validators.dart';
import 'auth_repository.dart';

/// Haqiqiy backend (`/v1/auth/*`) bilan ishlaydi. Faqat `API_MODE=real` da ishlatiladi.
/// DIQQAT: backend HTTP qatlami va bu klient birga hali ishga tushirib tekshirilmagan.
class HttpAuthRepository implements AuthRepository {
  HttpAuthRepository(this._api, this._tokens);

  final ApiClient _api;
  final TokenStore _tokens;

  @override
  Future<String> requestOtp(String phone) async {
    final normalized = normalizePhone(phone);
    if (normalized == null) {
      throw const AuthException('VALIDATION_ERROR', "Telefon raqami noto'g'ri");
    }
    final res = await _call(() => _api.post('/v1/auth/otp/request', body: {'phone': normalized}));
    final id = res?['challenge_id'];
    if (id is! String) throw const AuthException('SERVER_ERROR', 'Server javobi noto\'g\'ri');
    await _tokens.savePhone(maskPhone(normalized)); // faqat maskalangani saqlanadi
    return id;
  }

  @override
  Future<void> verifyOtp({required String challengeId, required String code}) async {
    final res = await _call(
      () => _api.post('/v1/auth/otp/verify', body: {'challenge_id': challengeId, 'code': code}),
    );
    await _saveFromResponse(res);
    await _tokens.savePinSet(res?['pin_set'] == true);
  }

  @override
  Future<bool> hasPin() async {
    final refresh = await _tokens.readRefresh();
    return refresh != null && await _tokens.readPinSet();
  }

  @override
  Future<void> createPin(String pin) async {
    if (!isPinAcceptable(pin)) {
      throw const AuthException('PIN_WEAK', 'PIN juda oddiy');
    }
    final access = await _tokens.readAccess();
    if (access == null) {
      throw const AuthException('TOKEN_INVALID', 'Qaytadan kiring');
    }
    await _call(() => _api.post('/v1/auth/pin/set', body: {'pin': pin}, bearer: access));
    await _tokens.savePinSet(true);
  }

  /// `true` — PIN to'g'ri. `false` — noto'g'ri. Bloklangan/boshqa xatolarda [AuthException].
  @override
  Future<bool> verifyPin(String pin) async {
    final refresh = await _tokens.readRefresh();
    if (refresh == null) {
      throw const AuthException('TOKEN_INVALID', 'Qaytadan kiring');
    }
    try {
      final res = await _api.post('/v1/auth/pin/login', body: {'refresh_token': refresh, 'pin': pin});
      await _saveFromResponse(res);
      return true;
    } on ApiException catch (e) {
      if (e.code == 'PIN_INVALID') return false;
      if (e.code == 'TOKEN_INVALID' || e.code == 'TOKEN_REUSE_DETECTED') {
        // Refresh token yaroqsiz: qurilmadan o'chirib, qayta OTP bilan kirish kerak.
        await _tokens.clear();
      }
      throw _toAuth(e);
    }
  }

  @override
  Future<String?> maskedPhone() => _tokens.readPhone();

  /// Faqat qurilmadagi tokenlarni o'chiradi. Backendda tokenni bekor qilish endpointi yo'q,
  /// shuning uchun refresh token serverda muddati tugaguncha amal qiladi (keyingi bosqich).
  @override
  Future<void> logout() => _tokens.clear();

  // --- ichki ---

  Future<Map<String, dynamic>?> _call(Future<Map<String, dynamic>?> Function() fn) async {
    try {
      return await fn();
    } on ApiException catch (e) {
      throw _toAuth(e);
    }
  }

  Future<void> _saveFromResponse(Map<String, dynamic>? res) async {
    final access = res?['access_token'];
    final refresh = res?['refresh_token'];
    if (access is! String || refresh is! String) {
      throw const AuthException('SERVER_ERROR', 'Server javobi noto\'g\'ri');
    }
    await _tokens.saveTokens(access: access, refresh: refresh);
  }

  AuthException _toAuth(ApiException e) {
    if (e.code == 'PIN_LOCKED') {
      final secs = e.details?['retry_after'];
      final mins = secs is int ? (secs / 60).ceil() : null;
      final msg = mins == null
          ? 'PIN vaqtincha bloklangan. Keyinroq urinib ko\'ring'
          : 'PIN bloklangan. $mins daqiqadan keyin urinib ko\'ring';
      return AuthException(e.code, msg);
    }
    if (e.code == 'OTP_RATE_LIMITED') {
      return AuthException(e.code, "Juda ko'p so'rov. Birozdan keyin urinib ko'ring");
    }
    return AuthException(e.code, e.message);
  }
}
