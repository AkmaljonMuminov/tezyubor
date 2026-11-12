import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:go_router/go_router.dart';

import '../../../core/assets.dart';
import '../../../core/l10n/strings.dart';
import '../../../core/router.dart';
import '../../../core/theme/app_colors.dart';
import '../../../shared/service_icon.dart';
import '../../../shared/test_mode_banner.dart';
import '../data/wallet_repository.dart';

/// "O'tkazmalar" bo'limi: o'tkazma turlari va so'nggi qabul qiluvchilar.
class TransfersScreen extends ConsumerWidget {
  const TransfersScreen({super.key});

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    final recipients = ref.watch(recipientsProvider);
    return SafeArea(
      child: Column(
        children: [
          const TestModeBanner(),
          Expanded(
            child: ListView(
              padding: const EdgeInsets.all(20),
              children: [
                Text(Strings.transfersTitle, style: Theme.of(context).textTheme.headlineSmall),
                const SizedBox(height: 16),
                Row(
                  children: [
                    Expanded(
                      child: _TypeCard(
                        icon: AppAssets.icTransfer,
                        label: Strings.transferToCard,
                        onTap: () => context.push(Routes.transfer),
                      ),
                    ),
                    const SizedBox(width: 12),
                    Expanded(
                      child: _TypeCard(
                        icon: AppAssets.icCard,
                        label: Strings.transferOwnTitle,
                        onTap: () => context.push(Routes.transferOwn),
                      ),
                    ),
                  ],
                ),
                const SizedBox(height: 24),
                Text(Strings.recentRecipients, style: Theme.of(context).textTheme.titleMedium),
                const SizedBox(height: 8),
                recipients.when(
                  data: (list) => list.isEmpty
                      ? const Padding(
                          padding: EdgeInsets.symmetric(vertical: 12),
                          child: Text(Strings.noRecipients, style: TextStyle(color: AppColors.muted)),
                        )
                      : Column(
                          children: [
                            for (final r in list)
                              Card(
                                elevation: 0,
                                margin: const EdgeInsets.only(bottom: 8),
                                child: ListTile(
                                  leading: const ServiceIcon(AppAssets.icProfile, size: 44),
                                  title: Text(r.masked),
                                  trailing: const Icon(Icons.chevron_right),
                                  onTap: () => context.push(Routes.transfer, extra: r.cardNumber),
                                ),
                              ),
                          ],
                        ),
                  loading: () => const Padding(
                    padding: EdgeInsets.all(16),
                    child: Center(child: CircularProgressIndicator()),
                  ),
                  error: (_, __) => Column(
                    children: [
                      const Text(Strings.genericError),
                      TextButton(
                        onPressed: () => ref.invalidate(recipientsProvider),
                        child: const Text(Strings.retry),
                      ),
                    ],
                  ),
                ),
              ],
            ),
          ),
        ],
      ),
    );
  }
}

class _TypeCard extends StatelessWidget {
  const _TypeCard({required this.icon, required this.label, required this.onTap});

  final String icon;
  final String label;
  final VoidCallback onTap;

  @override
  Widget build(BuildContext context) {
    return Card(
      elevation: 0,
      child: InkWell(
        borderRadius: BorderRadius.circular(12),
        onTap: onTap,
        child: Padding(
          padding: const EdgeInsets.all(16),
          child: Column(
            crossAxisAlignment: CrossAxisAlignment.start,
            children: [
              ServiceIcon(icon, size: 48),
              const SizedBox(height: 12),
              Text(label, style: const TextStyle(fontWeight: FontWeight.w600)),
            ],
          ),
        ),
      ),
    );
  }
}
