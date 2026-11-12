import 'package:flutter/material.dart';
import 'package:flutter/services.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:go_router/go_router.dart';

import '../../../core/format.dart';
import '../../../core/ids.dart';
import '../../../core/l10n/strings.dart';
import '../../../core/money.dart';
import '../../../core/router.dart';
import '../../../core/validators.dart';
import '../../../shared/card_picker.dart';
import '../../../shared/confirm_sheet.dart';
import '../../../shared/test_mode_banner.dart';
import '../data/wallet_repository.dart';
import '../domain/wallet_models.dart';

class TransferScreen extends ConsumerStatefulWidget {
  const TransferScreen({super.key, this.initialCard});

  /// So'nggi qabul qiluvchidan oldindan to'ldiriladigan karta raqami.
  final String? initialCard;

  @override
  ConsumerState<TransferScreen> createState() => _TransferScreenState();
}

class _TransferScreenState extends ConsumerState<TransferScreen> {
  final _cardCtrl = TextEditingController();
  final _amountCtrl = TextEditingController();
  String? _fromId;
  String? _cardError;
  String? _amountError;
  String? _error;
  bool _loading = false;

  /// Kiritilgan ma'lumot o'zgarsa yangilanadi; bir xil ma'lumot bilan qayta urinish — bir xil kalit.
  String _key = newIdempotencyKey();

  @override
  void initState() {
    super.initState();
    _cardCtrl.text = widget.initialCard ?? '';
  }

  @override
  void dispose() {
    _cardCtrl.dispose();
    _amountCtrl.dispose();
    super.dispose();
  }

  void _inputChanged() {
    _key = newIdempotencyKey();
    if (_error != null) setState(() => _error = null);
  }

  Future<void> _submit(List<CardInfo> cards) async {
    final to = normalizeCardNumber(_cardCtrl.text);
    final amount = parseAmountTiyin(_amountCtrl.text);
    setState(() {
      _cardError = to == null ? Strings.cardError : null;
      _amountError = amount == null ? Strings.amountError : null;
      _error = null;
    });
    final fromId = _fromId ?? (cards.isNotEmpty ? cards.first.id : null);
    if (to == null || amount == null || fromId == null) return;

    final fee = transferFeeTiyin(amount);
    final ok = await showConfirmSheet(
      context,
      title: Strings.transferTitle,
      rows: [
        MapEntry(Strings.toCard, groupDigits(to)),
        MapEntry(Strings.amountLabel, formatSom(amount)),
        MapEntry(Strings.fee, formatSom(fee)),
        MapEntry(Strings.total, formatSom(amount + fee)),
      ],
    );
    if (!ok || !mounted) return;

    setState(() => _loading = true);
    try {
      final txn = await ref.read(walletRepositoryProvider).transfer(
            fromCardId: fromId,
            toCardNumber: to,
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
    final cardsAsync = ref.watch(cardsProvider);
    return Scaffold(
      appBar: AppBar(title: const Text(Strings.transferTitle)),
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
                        controller: _cardCtrl,
                        enabled: !_loading,
                        keyboardType: TextInputType.number,
                        inputFormatters: [
                          FilteringTextInputFormatter.digitsOnly,
                          LengthLimitingTextInputFormatter(16),
                        ],
                        decoration: InputDecoration(
                          labelText: Strings.toCard,
                          hintText: Strings.cardHint,
                          errorText: _cardError,
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
