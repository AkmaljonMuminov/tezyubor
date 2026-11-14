import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:go_router/go_router.dart';

import '../../../core/l10n/strings.dart';
import '../../../core/router.dart';
import '../../../core/security/biometric_service.dart';
import '../../../core/theme/app_colors.dart';
import '../../../shared/pin_pad.dart';
import '../../../shared/test_mode_banner.dart';
import '../data/auth_repository.dart';

/// PIN bilan kirish. Barmoq izi yoqilgan va qurilmada mavjud bo'lsa, ekran ochilganda bir marta taklif qilinadi;
/// bekor qilinsa yoki xato bo'lsa PIN klaviaturasi doim ishlaydi (zaxira). PIN urinishlari cheklovi serverda.
/// PIN tiklash hali yo'q.
class PinLoginScreen extends ConsumerStatefulWidget {
  const PinLoginScreen({super.key});

  @override
  ConsumerState<PinLoginScreen> createState() => _PinLoginScreenState();
}

class _PinLoginScreenState extends ConsumerState<PinLoginScreen> {
  String? _error;
  bool _biometricReady = false;
  bool _busy = false;

  @override
  void initState() {
    super.initState();
    WidgetsBinding.instance.addPostFrameCallback((_) => _initBiometric());
  }

  Future<void> _initBiometric() async {
    try {
      final enabled = await ref.read(authRepositoryProvider).biometricEnabled();
      if (!enabled) return;
      final status = await ref.read(biometricServiceProvider).status();
      if (!mounted) return;
      if (status != BiometricStatus.available) return; // yozuvlar o'chirilgan bo'lishi mumkin: PIN bilan kiriladi
      setState(() => _biometricReady = true);
      await _tryBiometric(automatic: true);
    } catch (_) {
      // Biometrika yordamchi yo'l: har qanday xatoda PIN qoladi.
    }
  }

  Future<void> _tryBiometric({bool automatic = false}) async {
    if (_busy) return;
    _busy = true;
    try {
      final ok = await ref.read(biometricServiceProvider).authenticate(reason: Strings.biometricReason);
      if (!mounted) return;
      if (!ok) {
        // Avtomatik taklifda foydalanuvchi bekor qilgan bo'lsa xato ko'rsatmaymiz; tugma bosilgan bo'lsa ko'rsatamiz.
        if (!automatic) setState(() => _error = Strings.biometricFailed);
        return;
      }
      await ref.read(authRepositoryProvider).refreshSession();
      if (!mounted) return;
      context.go(Routes.home);
    } on AuthException catch (e) {
      if (!mounted) return;
      _handleAuthError(e);
    } catch (_) {
      if (mounted) setState(() => _error = Strings.genericError);
    } finally {
      _busy = false;
    }
  }

  void _handleAuthError(AuthException e) {
    if (e.code == 'TOKEN_INVALID' || e.code == 'TOKEN_REUSE_DETECTED') {
      // Sessiya yaroqsiz (masalan boshqa qurilmadan uzilgan) — telefon orqali qayta kirish.
      context.go(Routes.phone);
    } else {
      setState(() => _error = e.message);
    }
  }

  Future<void> _onCompleted(String pin) async {
    try {
      final ok = await ref.read(authRepositoryProvider).verifyPin(pin);
      if (!mounted) return;
      if (ok) {
        context.go(Routes.home);
      } else {
        setState(() => _error = Strings.pinWrong);
      }
    } on AuthException catch (e) {
      if (!mounted) return;
      _handleAuthError(e);
    } catch (_) {
      if (mounted) setState(() => _error = Strings.genericError);
    }
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      body: SafeArea(
        child: Column(
          children: [
            const TestModeBanner(),
            const SizedBox(height: 48),
            Text(Strings.pinLoginTitle, style: Theme.of(context).textTheme.headlineSmall),
            const SizedBox(height: 32),
            PinPad(onCompleted: _onCompleted, errorText: _error),
            if (_biometricReady) ...[
              const SizedBox(height: 8),
              TextButton.icon(
                key: const Key('biometric-login'),
                onPressed: () => _tryBiometric(),
                icon: const Icon(Icons.fingerprint, color: AppColors.primary),
                label: const Text(Strings.biometricLogin),
              ),
            ],
          ],
        ),
      ),
    );
  }
}
