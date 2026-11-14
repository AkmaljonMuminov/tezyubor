import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:go_router/go_router.dart';

import '../../core/brand.dart';
import '../../core/l10n/strings.dart';
import '../../core/router.dart';
import '../../core/security/biometric_service.dart';
import '../../core/theme/app_colors.dart';
import '../../shared/test_mode_banner.dart';
import '../auth/data/auth_repository.dart';
import '../wallet/data/ui_state.dart';
import '../wallet/data/wallet_repository.dart';

final _maskedPhoneProvider = FutureProvider<String?>(
  (ref) => ref.watch(authRepositoryProvider).maskedPhone(),
);

/// Biometrik holati + shu qurilmada yoqilganmi. Profil ochilganda qayta o'qiladi.
final _biometricProvider = FutureProvider.autoDispose<({BiometricStatus status, bool enabled})>((ref) async {
  final status = await ref.watch(biometricServiceProvider).status();
  final enabled = await ref.watch(authRepositoryProvider).biometricEnabled();
  return (status: status, enabled: enabled && status == BiometricStatus.available);
});

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
    ref.invalidate(_biometricProvider);
    ref.read(balanceHiddenProvider.notifier).state = false;
    if (context.mounted) context.go(Routes.phone);
  }

  /// Yoqishdan oldin biometrik tasdiq so'raladi (foydalanuvchi haqiqatan ishlata olishini tekshirish uchun).
  Future<void> _toggleBiometric(BuildContext context, WidgetRef ref, bool value) async {
    final repo = ref.read(authRepositoryProvider);
    if (value) {
      final ok = await ref.read(biometricServiceProvider).authenticate(reason: Strings.biometricReason);
      if (!ok) return;
    }
    await repo.setBiometricEnabled(value);
    ref.invalidate(_biometricProvider);
  }

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    final phone = ref.watch(_maskedPhoneProvider).valueOrNull;
    final bio = ref.watch(_biometricProvider).valueOrNull;
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
                        backgroundColor: AppColors.navy,
                        child: Icon(Icons.person, color: AppColors.goldLight, size: 30),
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
                      if (bio != null && bio.status != BiometricStatus.notSupported && bio.status != BiometricStatus.unavailable) ...[
                        SwitchListTile(
                          key: const Key('biometric-switch'),
                          secondary: const Icon(Icons.fingerprint),
                          title: const Text(Strings.biometricSetting),
                          subtitle: Text(
                            bio.status == BiometricStatus.notEnrolled
                                ? Strings.biometricNotEnrolled
                                : Strings.biometricSettingHint,
                          ),
                          value: bio.enabled,
                          onChanged: bio.status == BiometricStatus.available
                              ? (v) => _toggleBiometric(context, ref, v)
                              : null,
                        ),
                        const Divider(height: 1),
                      ],
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
