import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';

import '../../../core/format.dart';
import '../../../core/l10n/strings.dart';
import '../../../core/money.dart';
import '../../../core/theme/app_colors.dart';
import '../../../shared/test_mode_banner.dart';
import '../../../shared/txn_tile.dart';
import '../data/wallet_repository.dart';
import '../domain/wallet_models.dart';

/// "Monitoring": shu oydagi tushum/xarajat va kunlar bo'yicha guruhlangan operatsiyalar.
class MonitoringScreen extends ConsumerStatefulWidget {
  const MonitoringScreen({super.key});

  @override
  ConsumerState<MonitoringScreen> createState() => _MonitoringScreenState();
}

class _MonitoringScreenState extends ConsumerState<MonitoringScreen> {
  TxnFilter _filter = TxnFilter.all;

  @override
  Widget build(BuildContext context) {
    final txns = ref.watch(transactionsProvider);
    return SafeArea(
      child: Column(
        children: [
          const TestModeBanner(),
          Expanded(
            child: txns.when(
              loading: () => const Center(child: CircularProgressIndicator()),
              error: (_, __) => Center(
                child: Column(
                  mainAxisSize: MainAxisSize.min,
                  children: [
                    const Text(Strings.genericError),
                    TextButton(
                      onPressed: () => ref.invalidate(transactionsProvider),
                      child: const Text(Strings.retry),
                    ),
                  ],
                ),
              ),
              data: (all) => _Content(
                all: all,
                filter: _filter,
                onFilter: (f) => setState(() => _filter = f),
                onRefresh: () async {
                  ref.invalidate(transactionsProvider);
                  await ref.read(transactionsProvider.future);
                },
              ),
            ),
          ),
        ],
      ),
    );
  }
}

class _Content extends StatelessWidget {
  const _Content({
    required this.all,
    required this.filter,
    required this.onFilter,
    required this.onRefresh,
  });

  final List<Txn> all;
  final TxnFilter filter;
  final ValueChanged<TxnFilter> onFilter;
  final Future<void> Function() onRefresh;

  @override
  Widget build(BuildContext context) {
    final now = DateTime.now();
    final summary = summarizeMonth(all, now);
    final groups = groupByDay(applyFilter(all, filter));

    return RefreshIndicator(
      onRefresh: onRefresh,
      child: ListView(
        physics: const AlwaysScrollableScrollPhysics(),
        padding: const EdgeInsets.all(20),
        children: [
          Text(Strings.monitoringTitle, style: Theme.of(context).textTheme.headlineSmall),
          const SizedBox(height: 4),
          const Text(Strings.thisMonth, style: TextStyle(color: AppColors.muted)),
          const SizedBox(height: 12),
          Row(
            children: [
              Expanded(
                child: _SummaryCard(
                  label: Strings.incomes,
                  value: formatSom(summary.incomeTiyin, signed: summary.incomeTiyin > 0),
                  color: AppColors.primaryDark,
                ),
              ),
              const SizedBox(width: 12),
              Expanded(
                child: _SummaryCard(
                  label: Strings.expenses,
                  value: formatSom(summary.expenseTiyin == 0 ? 0 : -summary.expenseTiyin),
                  color: AppColors.error,
                ),
              ),
            ],
          ),
          const SizedBox(height: 16),
          Wrap(
            spacing: 8,
            children: [
              _FilterChip(Strings.filterAll, TxnFilter.all, filter, onFilter),
              _FilterChip(Strings.incomes, TxnFilter.income, filter, onFilter),
              _FilterChip(Strings.expenses, TxnFilter.expense, filter, onFilter),
            ],
          ),
          const SizedBox(height: 8),
          if (groups.isEmpty)
            const Padding(
              padding: EdgeInsets.symmetric(vertical: 32),
              child: Center(child: Text(Strings.noOperations)),
            )
          else
            for (final g in groups) ...[
              Padding(
                padding: const EdgeInsets.only(top: 16, bottom: 4),
                child: Text(
                  dayLabel(g.key, now),
                  style: const TextStyle(color: AppColors.muted, fontWeight: FontWeight.w600),
                ),
              ),
              for (final t in g.value) TxnTile(t),
            ],
        ],
      ),
    );
  }
}

class _SummaryCard extends StatelessWidget {
  const _SummaryCard({required this.label, required this.value, required this.color});

  final String label;
  final String value;
  final Color color;

  @override
  Widget build(BuildContext context) {
    return Container(
      padding: const EdgeInsets.all(14),
      decoration: BoxDecoration(color: AppColors.surface, borderRadius: BorderRadius.circular(16)),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Text(label, style: const TextStyle(fontWeight: FontWeight.w600)),
          const SizedBox(height: 6),
          Text(value, style: TextStyle(color: color, fontWeight: FontWeight.w800, fontSize: 16)),
        ],
      ),
    );
  }
}

class _FilterChip extends StatelessWidget {
  const _FilterChip(this.label, this.value, this.current, this.onSelected);

  final String label;
  final TxnFilter value;
  final TxnFilter current;
  final ValueChanged<TxnFilter> onSelected;

  @override
  Widget build(BuildContext context) {
    return ChoiceChip(
      label: Text(label),
      selected: value == current,
      onSelected: (_) => onSelected(value),
    );
  }
}
