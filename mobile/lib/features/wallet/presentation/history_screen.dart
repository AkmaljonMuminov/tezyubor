import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';

import '../../../core/l10n/strings.dart';
import '../../../shared/txn_tile.dart';
import '../data/wallet_repository.dart';

class HistoryScreen extends ConsumerWidget {
  const HistoryScreen({super.key});

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    final txns = ref.watch(transactionsProvider);
    return Scaffold(
      appBar: AppBar(title: const Text(Strings.history)),
      body: SafeArea(
        child: txns.when(
          data: (list) => list.isEmpty
              ? const Center(child: Text(Strings.noOperations))
              : ListView.builder(
                  padding: const EdgeInsets.symmetric(horizontal: 20),
                  itemCount: list.length,
                  itemBuilder: (_, i) => TxnTile(list[i]),
                ),
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
        ),
      ),
    );
  }
}
