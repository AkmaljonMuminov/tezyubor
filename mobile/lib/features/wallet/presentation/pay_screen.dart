import 'package:flutter/material.dart';
import 'package:flutter/services.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:go_router/go_router.dart';

import '../../../core/ids.dart';
import '../../../core/l10n/strings.dart';
import '../../../core/money.dart';
import '../../../core/router.dart';
import '../../../core/validators.dart';
import '../../../shared/card_picker.dart';
import '../../../shared/confirm_sheet.dart';
import '../../../shared/service_icon.dart';
import '../../../shared/test_mode_banner.dart';
import '../data/wallet_repository.dart';
import '../domain/wallet_models.dart';

/// Kategoriya bo'yicha xizmatlar ro'yxati.
class PayScreen extends StatelessWidget {
  const PayScreen({super.key, required this.category});

  final ServiceCategory category;

  @override
  Widget build(BuildContext context) {
    final services = kPayServices.where((s) => s.category == category).toList();
    return Scaffold(
      appBar: AppBar(
        title: Text(category == ServiceCategory.mobile ? Strings.payMobileTitle : Strings.payBillsTitle),
      ),
      body: SafeArea(
        child: Column(
          children: [
            const TestModeBanner(),
            Expanded(
              child: ListView(
                padding: const EdgeInsets.all(20),
                children: [
                  for (final s in services)
                    ListTile(
                      contentPadding: EdgeInsets.zero,
                      leading: ServiceIcon(s.icon, size: 48),
                      title: Text(s.name),
                      trailing: const Icon(Icons.chevron_right),
                      onTap: () => context.push(Routes.payForm, extra: s),
                    ),
                ],
              ),
            ),
          ],
        ),
      ),
    );
  }
}

/// Tanlangan xizmat uchun to'lov formasi.
class PayFormScreen extends ConsumerStatefulWidget {
  const PayFormScreen({super.key, required this.service});

  final PayService service;

  @override
  ConsumerState<PayFormScreen> createState() => _PayFormScreenState();
}

class _PayFormScreenState extends ConsumerState<PayFormScreen> {
  final _accountCtrl = TextEditingController();
  final _amountCtrl = TextEditingController();
  String? _fromId;
  String? _accountError;
  String? _amountError;
  String? _error;
  bool _loading = false;
  String _key = newIdempotencyKey();

  @override
  void dispose() {
    _accountCtrl.dispose();
    _amountCtrl.dispose();
    super.dispose();
  }

  void _inputChanged() {
    _key = newIdempotencyKey();
    if (_error != null) setState(() => _error = null);
  }

  Future<void> _submit(List<CardInfo> cards) async {
    final s = widget.service;
    final digits = _accountCtrl.text.replaceAll(RegExp(r'\D'), '');
    final amount = parseAmountTiyin(_amountCtrl.text);
    final accountOk = digits.length == s.accountDigits;
    setState(() {
      _accountError = accountOk ? null : Strings.accountError;
      _amountError = amount == null ? Strings.amountError : null;
      _error = null;
    });
    final fromId = _fromId ?? (cards.isNotEmpty ? cards.first.id : null);
    if (!accountOk || amount == null || fromId == null) return;

    final ok = await showConfirmSheet(
      context,
      title: s.name,
      rows: [
        MapEntry(s.accountLabel, digits),
        MapEntry(Strings.amountLabel, formatSom(amount)),
        MapEntry(Strings.fee, formatSom(0)),
        MapEntry(Strings.total, formatSom(amount)),
      ],
    );
    if (!ok || !mounted) return;

    setState(() => _loading = true);
    try {
      final txn = await ref.read(walletRepositoryProvider).pay(
            fromCardId: fromId,
            serviceId: s.id,
            account: digits,
            amountTiyin: amount,
            idempotencyKey: _key,
          );
      ref.invalidate(cardsProvider);
      ref.invalidate(transactionsProvider);
      if (!mounted) return;
      context.go(Routes.result, extra: txn);
    } on WalletException catch (e) {
      if (mounted) setState(() => _error = e.message);
    } catch (_) {
      if (mounted) setState(() => _error = Strings.genericError);
    } finally {
      if (mounted) setState(() => _loading = false);
    }
  }

  @override
  Widget build(BuildContext context) {
    final s = widget.service;
    final cardsAsync = ref.watch(cardsProvider);
    return Scaffold(
      appBar: AppBar(title: Text(s.name)),
      body: SafeArea(
        child: Column(
          children: [
            const TestModeBanner(),
            Expanded(
              child: cardsAsync.when(
                loading: () => const Center(child: CircularProgressIndicator()),
                error: (_, __) => const Center(child: Text(Strings.genericError)),
                data: (cards) {
                  final selected = _fromId ?? (cards.isNotEmpty ? cards.first.id : null);
                  return ListView(
                    padding: const EdgeInsets.all(20),
                    children: [
                      const Text(Strings.fromCard),
                      const SizedBox(height: 8),
                      CardPicker(
                        cards: cards,
                        selectedId: selected,
                        onChanged: (id) {
                          setState(() => _fromId = id);
                          _inputChanged();
                        },
                      ),
                      const SizedBox(height: 16),
                      TextField(
                        controller: _accountCtrl,
                        enabled: !_loading,
                        keyboardType: TextInputType.number,
                        inputFormatters: [
                          FilteringTextInputFormatter.digitsOnly,
                          LengthLimitingTextInputFormatter(s.accountDigits),
                        ],
                        decoration: InputDecoration(
                          labelText: s.accountLabel,
                          errorText: _accountError,
                        ),
                        onChanged: (_) => _inputChanged(),
                      ),
                      const SizedBox(height: 12),
                      TextField(
                        controller: _amountCtrl,
                        enabled: !_loading,
                        keyboardType: TextInputType.number,
                        inputFormatters: [
                          FilteringTextInputFormatter.digitsOnly,
                          LengthLimitingTextInputFormatter(8),
                        ],
                        decoration: InputDecoration(
                          labelText: Strings.amount,
                          errorText: _amountError,
                        ),
                        onChanged: (_) => _inputChanged(),
                      ),
                      if (_error != null) ...[
                        const SizedBox(height: 12),
                        Text(_error!, style: TextStyle(color: Theme.of(context).colorScheme.error)),
                      ],
                      const SizedBox(height: 20),
                      FilledButton(
                        onPressed: _loading ? null : () => _submit(cards),
                        child: _loading
                            ? const SizedBox(
                                height: 22,
                                width: 22,
                                child: CircularProgressIndicator(strokeWidth: 2.5, color: Colors.white),
                              )
                            : const Text(Strings.next),
                      ),
                    ],
                  );
                },
              ),
            ),
          ],
        ),
      ),
    );
  }
}
