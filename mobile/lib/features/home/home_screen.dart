import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:go_router/go_router.dart';

import '../../core/assets.dart';
import '../../core/brand.dart';
import '../../core/l10n/strings.dart';
import '../../core/money.dart';
import '../../core/router.dart';
import '../../core/theme/app_colors.dart';
import '../../shared/service_icon.dart';
import '../../shared/test_mode_banner.dart';
import '../../shared/txn_tile.dart';
import '../wallet/data/ui_state.dart';
import '../wallet/data/wallet_repository.dart';
import '../wallet/domain/wallet_models.dart';

class HomeScreen extends ConsumerWidget {
  const HomeScreen({super.key});

  Future<void> _refresh(WidgetRef ref) async {
    ref.invalidate(cardsProvider);
    ref.invalidate(transactionsProvider);
    await ref.read(cardsProvider.future);
  }

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    final cards = ref.watch(cardsProvider);
    final txns = ref.watch(transactionsProvider);

    return Scaffold(
      body: SafeArea(
        child: Column(
          children: [
            const TestModeBanner(),
            Expanded(
              child: RefreshIndicator(
                onRefresh: () => _refresh(ref),
                child: ListView(
                  physics: const AlwaysScrollableScrollPhysics(),
                  padding: const EdgeInsets.all(20),
                  children: [
                    const Text(
                      AppBrand.name,
                      style: TextStyle(fontSize: 22, fontWeight: FontWeight.w800, color: AppColors.primaryDark),
                    ),
                    const SizedBox(height: 16),
                    _BalanceCard(cards: cards),
                    const SizedBox(height: 20),
                    const _QuickActions(),
                    const SizedBox(height: 24),
                    Text(Strings.myCards, style: Theme.of(context).textTheme.titleMedium),
                    const SizedBox(height: 8),
                    cards.when(
                      data: (list) => list.isEmpty
                          ? const Text(Strings.noCards)
                          : Column(children: [for (final c in list) _CardRow(c)]),
                      loading: () => const _Loading(),
                      error: (_, __) => _ErrorRetry(onRetry: () => ref.invalidate(cardsProvider)),
                    ),
                    const SizedBox(height: 24),
                    Row(
                      mainAxisAlignment: MainAxisAlignment.spaceBetween,
                      children: [
                        Text(Strings.recent, style: Theme.of(context).textTheme.titleMedium),
                        TextButton(
                          onPressed: () => context.go(Routes.monitoring),
                          child: const Text(Strings.all),
                        ),
                      ],
                    ),
                    txns.when(
                      data: (list) => list.isEmpty
                          ? const Padding(
                              padding: EdgeInsets.symmetric(vertical: 12),
                              child: Text(Strings.noOperations),
                            )
                          : Column(children: [for (final t in list.take(5)) TxnTile(t)]),
                      loading: () => const _Loading(),
                      error: (_, __) => _ErrorRetry(onRetry: () => ref.invalidate(transactionsProvider)),
                    ),
                  ],
                ),
              ),
            ),
          ],
        ),
      ),
    );
  }
}

class _BalanceCard extends ConsumerWidget {
  const _BalanceCard({required this.cards});

  final AsyncValue<List<CardInfo>> cards;

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    final hidden = ref.watch(balanceHiddenProvider);
    final text = hidden
        ? Strings.hiddenAmount
        : cards.when(
            data: (list) => formatSom(list.fold<int>(0, (sum, c) => sum + c.balanceTiyin)),
            loading: () => '\u2026',
            error: (_, __) => '\u2014',
          );
    return Container(
      padding: const EdgeInsets.all(20),
      decoration: BoxDecoration(
        color: AppColors.primary,
        borderRadius: BorderRadius.circular(22),
      ),
      child: Row(
        children: [
          Expanded(
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                const Text(Strings.totalBalance, style: TextStyle(color: Color(0xFFE9FFF0))),
                const SizedBox(height: 8),
                Text(
                  text,
                  style: const TextStyle(color: Colors.white, fontSize: 30, fontWeight: FontWeight.w800),
                ),
              ],
            ),
          ),
          IconButton(
            tooltip: Strings.hideBalance,
            onPressed: () => ref.read(balanceHiddenProvider.notifier).state = !hidden,
            icon: Icon(hidden ? Icons.visibility_off : Icons.visibility, color: Colors.white),
          ),
        ],
      ),
    );
  }
}

class _QuickActions extends StatelessWidget {
  const _QuickActions();

  @override
  Widget build(BuildContext context) {
    return Row(
      mainAxisAlignment: MainAxisAlignment.spaceBetween,
      children: [
        _Action(AppAssets.icTransfer, Strings.actionTransfer, () => context.push(Routes.transfer)),
        _Action(AppAssets.icMobile, Strings.actionMobile,
            () => context.push(Routes.pay, extra: payCategoryById('mobile'))),
        _Action(AppAssets.icBills, Strings.actionBills,
            () => context.push(Routes.pay, extra: payCategoryById('bills'))),
        _Action(AppAssets.icHistory, Strings.actionHistory, () => context.go(Routes.monitoring)),
      ],
    );
  }
}

class _Action extends StatelessWidget {
  const _Action(this.icon, this.label, this.onTap);

  final String icon;
  final String label;
  final VoidCallback onTap;

  @override
  Widget build(BuildContext context) {
    return InkWell(
      borderRadius: BorderRadius.circular(16),
      onTap: onTap,
      child: SizedBox(
        width: 76,
        child: Column(
          children: [
            ServiceIcon(icon),
            const SizedBox(height: 6),
            Text(label, textAlign: TextAlign.center, style: const TextStyle(fontSize: 12)),
          ],
        ),
      ),
    );
  }
}

class _CardRow extends ConsumerWidget {
  const _CardRow(this.card);

  final CardInfo card;

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    final hidden = ref.watch(balanceHiddenProvider);
    return Container(
      margin: const EdgeInsets.only(bottom: 8),
      padding: const EdgeInsets.all(14),
      decoration: BoxDecoration(
        color: AppColors.surface,
        borderRadius: BorderRadius.circular(14),
      ),
      child: Row(
        children: [
          const ServiceIcon(AppAssets.icCard, size: 44),
          const SizedBox(width: 12),
          Expanded(
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                Text('${card.network} ${card.masked}',
                    style: const TextStyle(fontWeight: FontWeight.w700)),
                Text(hidden ? Strings.hiddenAmount : formatSom(card.balanceTiyin),
                    style: const TextStyle(color: AppColors.muted)),
              ],
            ),
          ),
        ],
      ),
    );
  }
}

class _Loading extends StatelessWidget {
  const _Loading();

  @override
  Widget build(BuildContext context) => const Padding(
        padding: EdgeInsets.all(16),
        child: Center(child: CircularProgressIndicator()),
      );
}

class _ErrorRetry extends StatelessWidget {
  const _ErrorRetry({required this.onRetry});

  final VoidCallback onRetry;

  @override
  Widget build(BuildContext context) {
    return Column(
      children: [
        const Text(Strings.genericError),
        TextButton(onPressed: onRetry, child: const Text(Strings.retry)),
      ],
    );
  }
}
