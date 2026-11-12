import 'package:flutter/material.dart';
import 'package:flutter/services.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:go_router/go_router.dart';

import '../../../core/ids.dart';
import '../../../core/l10n/strings.dart';
import '../../../core/money.dart';
import '../../../core/router.dart';
import '../../../core/theme/app_colors.dart';
import '../../../core/validators.dart';
import '../../../shared/card_picker.dart';
import '../../../shared/confirm_sheet.dart';
import '../../../shared/service_icon.dart';
import '../../../shared/test_mode_banner.dart';
import '../data/wallet_repository.dart';
import '../domain/wallet_models.dart';

/// To'lov formasiga beriladigan argumentlar. [account]/[amountTiyin] — tanlangan to'lovdan oldindan to'ldirish.
class PayFormArgs {
  const PayFormArgs({required this.service, this.account, this.amountTiyin});

  final PayService service;
  final String? account;
  final int? amountTiyin;
}

/// Kategoriya bo'yicha xizmatlar ro'yxati. Xizmat bo'lmasa — "Tez orada".
class PayScreen extends StatelessWidget {
  const PayScreen({super.key, required this.category});

  final PayCategory category;

  @override
  Widget build(BuildContext context) {
    final services = servicesOf(category.id);
    return Scaffold(
      appBar: AppBar(title: Text(category.name)),
      body: SafeArea(
        child: Column(
          children: [
            const TestModeBanner(),
            Expanded(
              child: services.isEmpty
                  ? Center(
                      child: Padding(
                        padding: const EdgeInsets.all(32),
                        child: Column(
                          mainAxisSize: MainAxisSize.min,
                          children: [
                            Icon(category.icon, size: 56, color: AppColors.muted),
                            const SizedBox(height: 16),
                            Text(Strings.soon, style: Theme.of(context).textTheme.titleLarge),
                            const SizedBox(height: 8),
                            const Text(Strings.soonBody, textAlign: TextAlign.center),
                          ],
                        ),
                      ),
                    )
                  : ListView(
                      padding: const EdgeInsets.all(20),
                      children: [
                        for (final s in services)
                          ListTile(
                            contentPadding: EdgeInsets.zero,
                            leading: ServiceIcon(s.icon, size: 48),
                            title: Text(s.name),
                            trailing: const Icon(Icons.chevron_right),
                            onTap: () => context.push(Routes.payForm, extra: PayFormArgs(service: s)),
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
  const PayFormScreen({super.key, required this.args});

  final PayFormArgs args;

  @override
  ConsumerState<PayFormScreen> createState() => _PayFormScreenState();
}

class _PayFormScreenState extends ConsumerState<PayFormScreen> {
  final _accountCtrl = TextEditingController();
  final _amountCtrl = TextEditingController();
  String? _fromId;
  bool _saveFavorite = false;
  String? _accountError;
  String? _amountError;
  String? _error;
  bool _loading = false;
  String _key = newIdempotencyKey();

  @override
  void initState() {
    super.initState();
    _accountCtrl.text = widget.args.account ?? '';
    final amount = widget.args.amountTiyin;
    if (amount != null) _amountCtrl.text = (amount ~/ 100).toString();
  }

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
    final s = widget.args.service;
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
      if (_saveFavorite) {
        // To'lov allaqachon bajarilgan; shablonni saqlash muvaffaqiyatsiz bo'lsa ham natijani ko'rsatamiz.
        try {
          await ref.read(walletRepositoryProvider).addFavorite(
                serviceId: s.id,
                account: digits,
                amountTiyin: amount,
              );
        } catch (_) {
          // e'tiborsiz
        } finally {
          ref.invalidate(favoritesProvider);
        }
      }
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
    final s = widget.args.service;
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
                      CheckboxListTile(
                        contentPadding: EdgeInsets.zero,
                        controlAffinity: ListTileControlAffinity.leading,
                        value: _saveFavorite,
                        onChanged: _loading ? null : (v) => setState(() => _saveFavorite = v ?? false),
                        title: const Text(Strings.saveFavorite),
                      ),
                      if (_error != null) ...[
                        const SizedBox(height: 4),
                        Text(_error!, style: TextStyle(color: Theme.of(context).colorScheme.error)),
                      ],
                      const SizedBox(height: 16),
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
