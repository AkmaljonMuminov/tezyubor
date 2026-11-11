import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:go_router/go_router.dart';

import '../../../core/l10n/strings.dart';
import '../../../core/router.dart';
import '../../../core/validators.dart';
import '../../../shared/pin_pad.dart';
import '../../../shared/test_mode_banner.dart';
import '../data/auth_repository.dart';

class PinCreateScreen extends ConsumerStatefulWidget {
  const PinCreateScreen({super.key});

  @override
  ConsumerState<PinCreateScreen> createState() => _PinCreateScreenState();
}

class _PinCreateScreenState extends ConsumerState<PinCreateScreen> {
  String? _first;
  String? _error;

  Future<void> _onCompleted(String pin) async {
    if (_first == null) {
      if (!isPinAcceptable(pin)) {
        setState(() => _error = Strings.pinWeak);
        return;
      }
      setState(() {
        _first = pin;
        _error = null;
      });
      return;
    }
    if (pin != _first) {
      setState(() {
        _first = null;
        _error = Strings.pinMismatch;
      });
      return;
    }
    try {
      await ref.read(authRepositoryProvider).createPin(pin);
      if (!mounted) return;
      context.go(Routes.home);
    } on AuthException catch (e) {
      if (mounted) setState(() => _error = e.message);
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
            Text(
              _first == null ? Strings.pinCreateTitle : Strings.pinConfirmTitle,
              style: Theme.of(context).textTheme.headlineSmall,
            ),
            const SizedBox(height: 32),
            PinPad(onCompleted: _onCompleted, errorText: _error),
          ],
        ),
      ),
    );
  }
}
