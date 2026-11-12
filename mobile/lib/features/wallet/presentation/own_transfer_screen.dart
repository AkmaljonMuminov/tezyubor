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
import '../../../shared/test_mode_banner.dart';
import '../data/wallet_repository.dart';
import '../domain/wallet_models.dart';

/// O'z kartalari orasida o'tkazma (komissiyasiz).
class OwnTransferScreen extends ConsumerStatefulWidget {
  const OwnTransferScreen({super.key});

  @override
  ConsumerState<OwnTransferScreen> createState() => _OwnTransferScreenState();
}

class _OwnTransferScreenState extends ConsumerState<OwnTransferScreen> {
  final _amountCtrl = TextEditingController();
  String? _fromId;
  String? _toId;
  String? _amountError;
  String? _error;
  bool _loading = false;
  String _key = newIdempotencyKey();

  @override
  void dispose() {
    _amountCtrl.dispose();
    super.dispose();
  }

  void _inputChanged() {
    _key = newIdempotencyKey();
    if (_error != null) setState(() => _error = null);
  }

  Future<void> _submit(String fromId, String toId, List<CardInfo> cards) async {
    final amount = parseAmountTiyin(_amountCtrl.text);
    setState(() {
      _amountError = amount == null ? Strings.amountError : null;
      _error = null;
    });
    if (amount == null) return;

    final from = cards.firstWhere((c) => c.id == fromId);
    final to = cards.firstWhere((c) => c.id == toId);
    final ok = await showConfirmSheet(
      context,
      title: Strings.transferOwnTitle,
      rows: [
        MapEntry(Strings.fromCardOwn, '${from.network} ${from.masked}'),
        MapEntry(Strings.toCardOwn, '${to.network} ${to.masked}'),
        MapEntry(Strings.amountLabel, formatSom(amount)),
        MapEntry(Strings.fee, formatSom(0)),
      ],
    );
    if (!ok || !mounted) return;

    setState(() => _loading = true);
    try {
      final txn = await ref.read(walletRepositoryProvider).transferOwn(
            fromCardId: fromId,
            toCardId: toId,
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
      appBar: AppBar(title: const Text(Strings.transferOwnTitle)),
      body: SafeArea(
        child: Column(
          children: [
            const TestModeBanner(),
            Expanded(
              child: cardsAsync.when(
                loading: () => const Center(child: CircularProgressIndicator()),
                error: (_, __) => const Center(child: Text(Strings.genericError)),
                data: (cards) {
                  if (cards.length < 2) {
                    return const Center(
                      child: Padding(
                        padding: EdgeInsets.all(24),
                        child: Text(Strings.needTwoCards, textAlign: TextAlign.center),
                      ),
                    );
                  }
                  final fromId = cards.any((c) => c.id == _fromId) ? _fromId! : cards.first.id;
                  final others = cards.where((c) => c.id != fromId).toList();
                  final toId = others.any((c) => c.id == _toId) ? _toId! : others.first.id;
                  return ListView(
                    padding: const EdgeInsets.all(20),
                    children: [
                      const Text(Strings.fromCardOwn),
                      const SizedBox(height: 8),
                      CardPicker(
                        cards: cards,
                        selectedId: fromId,
                        onChanged: (id) {
                          setState(() => _fromId = id);
                          _inputChanged();
                        },
                      ),
                      const SizedBox(height: 12),
                      const Text(Strings.toCardOwn),
                      const SizedBox(height: 8),
                      CardPicker(
                        cards: others,
                        selectedId: toId,
                        onChanged: (id) {
                          setState(() => _toId = id);
                          _inputChanged();
                        },
                      ),
                      const SizedBox(height: 16),
                      TextField(
                        controller: _amountCtrl,
                        enabled: !_loading,
                        keyboardType: TextInputType.number,
                        inputFormatters: [
                          FilteringTextInputFormatter.digitsOnly,
                          LengthLimitingTextInputFormatter(8),
                        ],
                        decoration: InputDecoration(labelText: Strings.amount, errorText: _amountError),
                        onChanged: (_) => _inputChanged(),
                      ),
                      if (_error != null) ...[
                        const SizedBox(height: 12),
                        Text(_error!, style: TextStyle(color: Theme.of(context).colorScheme.error)),
                      ],
                      const SizedBox(height: 20),
                      FilledButton(
                        onPressed: _loading ? null : () => _submit(fromId, toId, cards),
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
