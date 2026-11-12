import 'package:flutter/material.dart';
import 'package:go_router/go_router.dart';

import '../../../core/assets.dart';
import '../../../core/l10n/strings.dart';
import '../../../core/router.dart';
import '../../../shared/service_icon.dart';
import '../../../shared/test_mode_banner.dart';
import '../domain/wallet_models.dart';

/// "To'lov" bo'limi: xizmat kategoriyalari.
class PayHubScreen extends StatelessWidget {
  const PayHubScreen({super.key});

  @override
  Widget build(BuildContext context) {
    return SafeArea(
      child: Column(
        children: [
          const TestModeBanner(),
          Expanded(
            child: ListView(
              padding: const EdgeInsets.all(20),
              children: [
                Text(Strings.payTitle, style: Theme.of(context).textTheme.headlineSmall),
                const SizedBox(height: 16),
                _CategoryTile(
                  icon: AppAssets.icMobile,
                  title: Strings.payMobileTitle,
                  onTap: () => context.push(Routes.pay, extra: ServiceCategory.mobile),
                ),
                _CategoryTile(
                  icon: AppAssets.icBills,
                  title: Strings.payBillsTitle,
                  onTap: () => context.push(Routes.pay, extra: ServiceCategory.bills),
                ),
              ],
            ),
          ),
        ],
      ),
    );
  }
}

class _CategoryTile extends StatelessWidget {
  const _CategoryTile({required this.icon, required this.title, required this.onTap});

  final String icon;
  final String title;
  final VoidCallback onTap;

  @override
  Widget build(BuildContext context) {
    return Card(
      elevation: 0,
      margin: const EdgeInsets.only(bottom: 10),
      child: ListTile(
        contentPadding: const EdgeInsets.symmetric(horizontal: 14, vertical: 6),
        leading: ServiceIcon(icon, size: 48),
        title: Text(title, style: const TextStyle(fontWeight: FontWeight.w600)),
        trailing: const Icon(Icons.chevron_right),
        onTap: onTap,
      ),
    );
  }
}
