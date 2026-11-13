import 'package:flutter/material.dart';

import '../core/brand.dart';
import '../core/l10n/strings.dart';

/// Test rejimida har doim ko'rinadi — foydalanuvchi sinov muhitini haqiqiydan ajrata olsin.
class TestModeBanner extends StatelessWidget {
  const TestModeBanner({super.key});

  @override
  Widget build(BuildContext context) {
    if (!kWalletIsMock) return const SizedBox.shrink();
    return Container(
      width: double.infinity,
      padding: const EdgeInsets.symmetric(vertical: 6, horizontal: 12),
      color: const Color(0xFFFFF1C2),
      child: const Text(
        kMockMode ? Strings.testMode : Strings.testWalletMode,
        textAlign: TextAlign.center,
        style: TextStyle(fontSize: 12, fontWeight: FontWeight.w600, color: Color(0xFF6B5200)),
      ),
    );
  }
}
