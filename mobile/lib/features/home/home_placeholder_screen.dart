import 'package:flutter/material.dart';

import '../../core/l10n/strings.dart';
import '../../shared/test_mode_banner.dart';

/// Vaqtincha: bosh sahifa 2-bosqichda yaratiladi. Soxta balans yoki ishlamaydigan tugma ko'rsatilmaydi.
class HomePlaceholderScreen extends StatelessWidget {
  const HomePlaceholderScreen({super.key});

  @override
  Widget build(BuildContext context) {
    return const Scaffold(
      body: SafeArea(
        child: Column(
          children: [
            TestModeBanner(),
            Expanded(
              child: Center(
                child: Padding(
                  padding: EdgeInsets.all(24),
                  child: Text(Strings.homePlaceholder, textAlign: TextAlign.center),
                ),
              ),
            ),
          ],
        ),
      ),
    );
  }
}
