import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:local_auth/local_auth.dart';

/// Qurilmada biometrik tasdiq imkoniyati.
enum BiometricStatus {
  /// Barmoq izi/yuz yozilgan va ishlatish mumkin.
  available,

  /// Qurilmada biometrik uskuna yo'q (yoki qo'llab-quvvatlanmaydi).
  notSupported,

  /// Uskuna bor, lekin hech narsa yozilmagan (sozlamalardan qo'shish kerak).
  notEnrolled,

  /// Vaqtincha ishlamaydi yoki holatni aniqlab bo'lmadi (plagin xatosi, bloklangan va h.k.).
  unavailable,
}

/// Biometrik tasdiq. MUHIM: bu faqat "ilovani shu qurilmada ochish" qulayligi. Natija kriptografik kalitga
/// BOG'LANMAGAN (`CryptoObject` yo'q), shuning uchun pul harakati uchun ishlatilmaydi — u serverda PIN bilan tasdiqlanadi.
abstract class BiometricService {
  Future<BiometricStatus> status();

  /// `true` — foydalanuvchi tasdiqladi. Bekor qilish, xato, bloklanish, mavjud emaslik — hammasi `false`
  /// (chaqiruvchi PIN'ga qaytadi). Hech qachon istisno tashlamaydi.
  Future<bool> authenticate({required String reason});
}

class LocalAuthBiometricService implements BiometricService {
  LocalAuthBiometricService([LocalAuthentication? auth]) : _auth = auth ?? LocalAuthentication();

  final LocalAuthentication _auth;

  @override
  Future<BiometricStatus> status() async {
    // Plagin yo'q (masalan testlarda) yoki platforma xatosi — hamma holatda `unavailable`, ilova yiqilmaydi.
    try {
      if (!await _auth.isDeviceSupported()) return BiometricStatus.notSupported;
      final enrolled = await _auth.getAvailableBiometrics();
      if (enrolled.isNotEmpty) return BiometricStatus.available;
      return await _auth.canCheckBiometrics ? BiometricStatus.notEnrolled : BiometricStatus.notSupported;
    } catch (_) {
      return BiometricStatus.unavailable;
    }
  }

  @override
  Future<bool> authenticate({required String reason}) async {
    try {
      return await _auth.authenticate(
        localizedReason: reason,
        options: const AuthenticationOptions(biometricOnly: true, stickyAuth: true),
      );
    } catch (_) {
      return false;
    }
  }
}

/// Testlar uchun.
class FakeBiometricService implements BiometricService {
  FakeBiometricService({this.fakeStatus = BiometricStatus.available, this.succeeds = true});

  BiometricStatus fakeStatus;
  bool succeeds;
  int authenticateCalls = 0;

  @override
  Future<BiometricStatus> status() async => fakeStatus;

  @override
  Future<bool> authenticate({required String reason}) async {
    authenticateCalls++;
    return succeeds;
  }
}

final biometricServiceProvider = Provider<BiometricService>((ref) => LocalAuthBiometricService());
