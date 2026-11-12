import 'package:flutter/material.dart';
import 'package:go_router/go_router.dart';

import '../../../core/format.dart';
import '../../../core/l10n/strings.dart';
import '../../../core/money.dart';
import '../../../core/router.dart';
import '../../../core/theme/app_colors.dart';
import '../../../shared/test_mode_banner.dart';
import '../domain/wallet_models.dart';

class ResultScreen extends StatelessWidget {
  const ResultScreen({super.key, required this.txn});

  final Txn txn;

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      body: SafeArea(
        child: Column(
          children: [
            const TestModeBanner(),
            Expanded(
              child: Padding(
                padding: const EdgeInsets.all(24),
                child: Column(
                  mainAxisAlignment: MainAxisAlignment.center,
                  children: [
                    const Icon(Icons.check_circle, size: 88, color: AppColors.primary),
                    const SizedBox(height: 16),
                    Text(Strings.success, style: Theme.of(context).textTheme.headlineSmall),
                    const SizedBox(height: 24),
                    Text(txn.title, textAlign: TextAlign.center),
                    const SizedBox(height: 8),
                    Text(
                      formatSom(txn.amountTiyin.abs()),
                      style: const TextStyle(fontSize: 30, fontWeight: FontWeight.w800),
                    ),
                    if (txn.feeTiyin > 0) ...[
                      const SizedBox(height: 4),
                      Text('${Strings.fee}: ${formatSom(txn.feeTiyin)}',
                          style: const TextStyle(color: AppColors.muted)),
                    ],
                    const SizedBox(height: 12),
                    Text(formatDateTime(txn.createdAt), style: const TextStyle(color: AppColors.muted)),
                    const SizedBox(height: 4),
                    Text('${Strings.operationId}: ${txn.id}',
                        style: const TextStyle(color: AppColors.muted, fontSize: 12)),
                  ],
                ),
              ),
            ),
            Padding(
              padding: const EdgeInsets.fromLTRB(24, 0, 24, 24),
              child: FilledButton(
                onPressed: () => context.go(Routes.home),
                child: const Text(Strings.done),
              ),
            ),
          ],
        ),
      ),
    );
  }
}
