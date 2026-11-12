import 'package:flutter/material.dart';
import 'package:flutter/services.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:go_router/go_router.dart';

import '../../../core/l10n/strings.dart';
import '../../../core/router.dart';
import '../../../shared/test_mode_banner.dart';
import '../data/auth_repository.dart';
import '../data/mock_auth_repository.dart';

class OtpScreen extends ConsumerStatefulWidget {
  const OtpScreen({super.key, required this.args});

  final OtpArgs args;

  @override
  ConsumerState<OtpScreen> createState() => _OtpScreenState();
}

class _OtpScreenState extends ConsumerState<OtpScreen> {
  final _controller = TextEditingController();
  bool _loading = false;
  String? _error;

  @override
  void dispose() {
    _controller.dispose();
    super.dispose();
  }

  Future<void> _verify(String code) async {
    setState(() {
      _loading = true;
      _error = null;
    });
    try {
      await ref
          .read(authRepositoryProvider)
          .verifyOtp(challengeId: widget.args.challengeId, code: code);
      final hasPin = await ref.read(authRepositoryProvider).hasPin();
      if (!mounted) return;
      context.go(hasPin ? Routes.pinLogin : Routes.pinCreate);
    } on AuthException catch (e) {
      if (mounted) {
        _controller.clear();
        setState(() => _error = e.message);
      }
    } catch (_) {
      if (mounted) setState(() => _error = Strings.genericError);
    } finally {
      if (mounted) setState(() => _loading = false);
    }
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      appBar: AppBar(backgroundColor: Colors.transparent, elevation: 0),
      body: SafeArea(
        child: Column(
          children: [
            const TestModeBanner(),
            Padding(
              padding: const EdgeInsets.all(24),
              child: Column(
                crossAxisAlignment: CrossAxisAlignment.start,
                children: [
                  Text(Strings.otpTitle, style: Theme.of(context).textTheme.headlineSmall),
                  const SizedBox(height: 8),
                  Text('+${widget.args.phone}'),
                  const SizedBox(height: 4),
                  const Text(Strings.otpSubtitle),
                  const SizedBox(height: 24),
                  TextField(
                    controller: _controller,
                    autofocus: true,
                    enabled: !_loading,
                    keyboardType: TextInputType.number,
                    textAlign: TextAlign.center,
                    inputFormatters: [
                      FilteringTextInputFormatter.digitsOnly,
                      LengthLimitingTextInputFormatter(6),
                    ],
                    style: const TextStyle(fontSize: 28, letterSpacing: 10, fontWeight: FontWeight.w700),
                    decoration: InputDecoration(errorText: _error),
                    onChanged: (v) {
                      if (v.length == 6) _verify(v);
                    },
                  ),
                  // Test rejimida kod ko'rsatiladi; haqiqiy rejimda hech qachon.
                  if (_isMock) ...[
                    const SizedBox(height: 12),
                    const Text('Test kodi: ${MockAuthRepository.testCode}',
                        style: TextStyle(fontSize: 12)),
                  ],
                ],
              ),
            ),
          ],
        ),
      ),
    );
  }

  bool get _isMock => ref.read(authRepositoryProvider) is MockAuthRepository;
}
