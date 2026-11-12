import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:go_router/go_router.dart';

import '../../core/brand.dart';
import '../../core/l10n/strings.dart';
import '../../core/router.dart';
import '../../core/theme/app_colors.dart';
import '../../shared/test_mode_banner.dart';
import '../auth/data/auth_repository.dart';
import '../wallet/data/ui_state.dart';
import '../wallet/data/wallet_repository.dart';

final _maskedPhoneProvider = FutureProvider<String?>(
  (ref) => ref.watch(authRepositoryProvider).maskedPhone(),
);

/// Profil: maskalangan telefon, sozlamalar, chiqish. Ism va hujjat ma'lumotlari yo'q (identifikatsiya hali qo'shilmagan).
class ProfileScreen extends ConsumerWidget {
  const ProfileScreen({super.key});

  Future<void> _logout(BuildContext context, WidgetRef ref) async {
    final ok = await showDialog<bool>(
      context: context,
      builder: (ctx) => AlertDialog(
        content: const Text(Strings.logoutConfirm),
        actions: [
          TextButton(onPressed: () => Navigator.of(ctx).pop(false), child: const Text(Strings.cancel)),
          TextButton(onPressed: () => Navigator.of(ctx).pop(true), child: const Text(Strings.logout)),
        ],
      ),
    );
    if (ok != true) return;
    await ref.read(authRepositoryProvider).logout();
    // Oldingi foydalanuvchi ma'lumotlari keyingi kirishda ko'rinib qolmasin.
    ref.invalidate(cardsProvider);
    ref.invalidate(transactionsProvider);
    ref.invalidate(recipientsProvider);
    ref.invalidate(_maskedPhoneProvider);
    ref.read(balanceHiddenProvider.notifier).state = false;
    if (context.mounted) context.go(Routes.phone);
  }

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    final phone = ref.watch(_maskedPhoneProvider).valueOrNull;
    final hidden = ref.watch(balanceHiddenProvider);

    return SafeArea(
      child: Column(
        children: [
          const TestModeBanner(),
          Expanded(
            child: ListView(
              padding: const EdgeInsets.all(20),
              children: [
                Text(Strings.profileTitle, style: Theme.of(context).textTheme.headlineSmall),
                const SizedBox(height: 16),
                Container(
                  padding: const EdgeInsets.all(16),
                  decoration: BoxDecoration(
                    color: AppColors.surface,
                    borderRadius: BorderRadius.circular(16),
                  ),
                  child: Row(
                    children: [
                      const CircleAvatar(
                        radius: 28,
                        backgroundColor: AppColors.tint,
                        child: Icon(Icons.person, color: AppColors.primaryDark, size: 30),
                      ),
                      const SizedBox(width: 14),
                      Expanded(
                        child: Column(
                          crossAxisAlignment: CrossAxisAlignment.start,
                          children: [
                            const Text(AppBrand.name, style: TextStyle(fontWeight: FontWeight.w700)),
                            const SizedBox(height: 2),
                            Text(phone ?? '—', style: const TextStyle(color: AppColors.muted)),
                          ],
                        ),
                      ),
                    ],
                  ),
                ),
                const SizedBox(height: 16),
                Container(
                  decoration: BoxDecoration(
                    color: AppColors.surface,
                    borderRadius: BorderRadius.circular(16),
                  ),
                  child: Column(
                    children: [
                      SwitchListTile(
                        secondary: const Icon(Icons.visibility_off_outlined),
                        title: const Text(Strings.hideBalance),
                        value: hidden,
                        onChanged: (v) => ref.read(balanceHiddenProvider.notifier).state = v,
                      ),
                      const Divider(height: 1),
                      const ListTile(
                        leading: Icon(Icons.language),
                        title: Text(Strings.language),
                        trailing: Text(Strings.languageValue, style: TextStyle(color: AppColors.muted)),
                      ),
                      const Divider(height: 1),
                      const ListTile(
                        leading: Icon(Icons.info_outline),
                        title: Text(Strings.version),
                        trailing: Text('0.1.0', style: TextStyle(color: AppColors.muted)),
                      ),
                    ],
                  ),
                ),
                const SizedBox(height: 16),
                OutlinedButton.icon(
                  onPressed: () => _logout(context, ref),
                  icon: const Icon(Icons.logout),
                  label: const Text(Strings.logout),
                  style: OutlinedButton.styleFrom(
                    minimumSize: const Size.fromHeight(52),
                    foregroundColor: AppColors.error,
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
