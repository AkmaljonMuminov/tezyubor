import 'package:flutter/material.dart';
import 'package:flutter/services.dart';
import 'package:go_router/go_router.dart';

import '../../../core/brand.dart';
import '../../../core/l10n/strings.dart';
import '../../../core/money.dart';
import '../../../core/router.dart';
import '../../../core/theme/app_colors.dart';
import '../../../shared/test_mode_banner.dart';
import '../domain/receipt.dart';
import '../domain/wallet_models.dart';

/// Chek. [fresh] — operatsiya hozirgina bajarilgan (muvaffaqiyat belgisi ko'rsatiladi, "Tayyor" bosh sahifaga qaytaradi).
/// Aks holda tarixdan ochilgan: orqaga qaytadi.
class ReceiptScreen extends StatelessWidget {
  const ReceiptScreen({super.key, required this.txn, this.fresh = false});

  final Txn txn;
  final bool fresh;

  Future<void> _copy(BuildContext context) async {
    await Clipboard.setData(ClipboardData(text: buildReceiptText(txn, test: kWalletIsMock)));
    if (!context.mounted) return;
    ScaffoldMessenger.of(context)
      ..hideCurrentSnackBar()
      ..showSnackBar(const SnackBar(content: Text(Strings.receiptCopied)));
  }

  void _close(BuildContext context) {
    if (fresh || !context.canPop()) {
      context.go(Routes.home);
    } else {
      context.pop();
    }
  }

  @override
  Widget build(BuildContext context) {
    final ok = txn.status == TxnStatus.succeeded;
    final lines = buildReceiptLines(txn);

    return PopScope(
      // Yangi chekdan tizim "orqaga" tugmasi bilan chiqilsa, to'lov formasiga emas, bosh sahifaga qaytamiz.
      canPop: !fresh,
      onPopInvokedWithResult: (didPop, _) {
        if (!didPop && fresh) context.go(Routes.home);
      },
      child: Scaffold(
        appBar: fresh
            ? null
            : AppBar(title: const Text(Strings.receiptTitle)),
        body: SafeArea(
          child: Column(
            children: [
              const TestModeBanner(),
              Expanded(
                child: ListView(
                  padding: const EdgeInsets.all(20),
                  children: [
                    if (fresh) ...[
                      const SizedBox(height: 8),
                      Icon(
                        ok ? Icons.check_circle : Icons.cancel,
                        size: 72,
                        color: ok ? AppColors.primary : AppColors.error,
                      ),
                      const SizedBox(height: 12),
                      Text(
                        ok ? Strings.success : Strings.operationFailed,
                        textAlign: TextAlign.center,
                        style: Theme.of(context).textTheme.headlineSmall,
                      ),
                      const SizedBox(height: 16),
                    ],
                    Container(
                      padding: const EdgeInsets.all(20),
                      decoration: BoxDecoration(
                        color: AppColors.surface,
                        borderRadius: BorderRadius.circular(18),
                      ),
                      child: Column(
                        crossAxisAlignment: CrossAxisAlignment.stretch,
                        children: [
                          Text(
                            AppBrand.name,
                            textAlign: TextAlign.center,
                            style: const TextStyle(
                              fontSize: 18,
                              fontWeight: FontWeight.w800,
                              color: AppColors.primaryDark,
                            ),
                          ),
                          if (kWalletIsMock)
                            const Padding(
                              padding: EdgeInsets.only(top: 6),
                              child: Text(
                                Strings.testReceipt,
                                textAlign: TextAlign.center,
                                style: TextStyle(
                                  fontSize: 12,
                                  fontWeight: FontWeight.w700,
                                  color: Color(0xFF6B5200),
                                ),
                              ),
                            ),
                          const SizedBox(height: 12),
                          Text(
                            formatSom(txn.amountTiyin.abs()),
                            textAlign: TextAlign.center,
                            style: const TextStyle(fontSize: 30, fontWeight: FontWeight.w800),
                          ),
                          const SizedBox(height: 8),
                          const Divider(),
                          for (final l in lines) _Row(l),
                        ],
                      ),
                    ),
                  ],
                ),
              ),
              Padding(
                padding: const EdgeInsets.fromLTRB(20, 0, 20, 16),
                child: Column(
                  children: [
                    OutlinedButton.icon(
                      onPressed: () => _copy(context),
                      icon: const Icon(Icons.copy),
                      label: const Text(Strings.copyReceipt),
                      style: OutlinedButton.styleFrom(minimumSize: const Size.fromHeight(52)),
                    ),
                    const SizedBox(height: 10),
                    FilledButton(
                      onPressed: () => _close(context),
                      child: const Text(Strings.done),
                    ),
                  ],
                ),
              ),
            ],
          ),
        ),
      ),
    );
  }
}

class _Row extends StatelessWidget {
  const _Row(this.line);

  final ReceiptLine line;

  @override
  Widget build(BuildContext context) {
    return Padding(
      padding: const EdgeInsets.symmetric(vertical: 7),
      child: Row(
        crossAxisAlignment: CrossAxisAlignment.start,
        mainAxisAlignment: MainAxisAlignment.spaceBetween,
        children: [
          Expanded(
            flex: 4,
            child: Text(line.label, style: const TextStyle(color: AppColors.muted)),
          ),
          const SizedBox(width: 12),
          Expanded(
            flex: 5,
            child: Text(
              line.value,
              textAlign: TextAlign.right,
              style: const TextStyle(fontWeight: FontWeight.w600),
            ),
          ),
        ],
      ),
    );
  }
}
