import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:go_router/go_router.dart';

import '../../../core/l10n/strings.dart';
import '../../../core/router.dart';
import '../../../shared/pin_pad.dart';
import '../../../shared/test_mode_banner.dart';
import '../data/auth_repository.dart';

/// Eslatma: PIN tiklash va biometrika hali yo'q (keyingi bosqich). Urinishlarni cheklash serverda bo'ladi.
class PinLoginScreen extends ConsumerStatefulWidget {
  const PinLoginScreen({super.key});

  @override
  ConsumerState<PinLoginScreen> createState() => _PinLoginScreenState();
}

class _PinLoginScreenState extends ConsumerState<PinLoginScreen> {
  String? _error;

  Future<void> _onCompleted(String pin) async {
    final ok = await ref.read(authRepositoryProvider).verifyPin(pin);
    if (!mounted) return;
    if (ok) {
      context.go(Routes.home);
    } else {
      setState(() => _error = Strings.pinWrong);
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
          ],
        ),
      ),
    );
  }
}
