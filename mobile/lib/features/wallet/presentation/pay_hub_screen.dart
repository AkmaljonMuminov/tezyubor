import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:go_router/go_router.dart';

import '../../../core/l10n/strings.dart';
import '../../../core/money.dart';
import '../../../core/router.dart';
import '../../../core/theme/app_colors.dart';
import '../../../shared/service_icon.dart';
import '../../../shared/test_mode_banner.dart';
import '../data/wallet_repository.dart';
import '../domain/wallet_models.dart';
import 'pay_screen.dart';

/// "To'lov" bo'limi: qidiruv, tanlangan to'lovlar va barcha kategoriyalar.
class PayHubScreen extends ConsumerStatefulWidget {
  const PayHubScreen({super.key});

  @override
  ConsumerState<PayHubScreen> createState() => _PayHubScreenState();
}

class _PayHubScreenState extends ConsumerState<PayHubScreen> {
  final _search = TextEditingController();
  String _query = '';

  @override
  void dispose() {
    _search.dispose();
    super.dispose();
  }

  Future<void> _confirmRemove(FavoritePayment f) async {
    final ok = await showDialog<bool>(
      context: context,
      builder: (ctx) => AlertDialog(
        content: const Text(Strings.removeFavoriteQ),
        actions: [
          TextButton(onPressed: () => Navigator.of(ctx).pop(false), child: const Text(Strings.cancel)),
          TextButton(onPressed: () => Navigator.of(ctx).pop(true), child: const Text(Strings.remove)),
        ],
      ),
    );
    if (ok != true) return;
    try {
      await ref.read(walletRepositoryProvider).removeFavorite(f.id);
    } finally {
      ref.invalidate(favoritesProvider);
    }
  }

  @override
  Widget build(BuildContext context) {
    final favorites = ref.watch(favoritesProvider).valueOrNull ?? const <FavoritePayment>[];
    final searching = _query.trim().isNotEmpty;
    final result = searchCatalog(_query);

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
                TextField(
                  controller: _search,
                  textInputAction: TextInputAction.search,
                  decoration: InputDecoration(
                    hintText: Strings.searchHint,
                    prefixIcon: const Icon(Icons.search),
                    suffixIcon: searching
                        ? IconButton(
                            icon: const Icon(Icons.close),
                            onPressed: () {
                              _search.clear();
                              setState(() => _query = '');
                            },
                          )
                        : null,
                  ),
                  onChanged: (v) => setState(() => _query = v),
                ),
                const SizedBox(height: 16),
                if (!searching && favorites.isNotEmpty) ...[
                  Text(Strings.favorites, style: Theme.of(context).textTheme.titleMedium),
                  const SizedBox(height: 8),
                  SizedBox(
                    height: 104,
                    child: ListView.separated(
                      scrollDirection: Axis.horizontal,
                      itemCount: favorites.length,
                      separatorBuilder: (_, __) => const SizedBox(width: 10),
                      itemBuilder: (_, i) => _FavoriteCard(
                        favorite: favorites[i],
                        onRemove: () => _confirmRemove(favorites[i]),
                      ),
                    ),
                  ),
                  const SizedBox(height: 20),
                ],
                if (searching && result.categories.isEmpty && result.services.isEmpty)
                  const Padding(
                    padding: EdgeInsets.symmetric(vertical: 32),
                    child: Center(child: Text(Strings.nothingFound)),
                  ),
                for (final s in result.services)
                  _ServiceResultTile(
                    service: s,
                    onTap: () => context.push(Routes.payForm, extra: PayFormArgs(service: s)),
                  ),
                for (final c in result.categories) _CategoryTile(category: c),
              ],
            ),
          ),
        ],
      ),
    );
  }
}

class _CategoryTile extends StatelessWidget {
  const _CategoryTile({required this.category});

  final PayCategory category;

  @override
  Widget build(BuildContext context) {
    final hasServices = servicesOf(category.id).isNotEmpty;
    return Card(
      elevation: 0,
      margin: const EdgeInsets.only(bottom: 10),
      child: ListTile(
        contentPadding: const EdgeInsets.symmetric(horizontal: 14, vertical: 4),
        leading: Container(
          width: 44,
          height: 44,
          decoration: BoxDecoration(color: AppColors.tint, borderRadius: BorderRadius.circular(12)),
          child: Icon(category.icon, color: AppColors.primaryDark),
        ),
        title: Text(category.name, style: const TextStyle(fontWeight: FontWeight.w600)),
        trailing: hasServices
            ? const Icon(Icons.chevron_right)
            : const Text(Strings.soon, style: TextStyle(color: AppColors.muted, fontSize: 12)),
        onTap: () => context.push(Routes.pay, extra: category),
      ),
    );
  }
}

class _ServiceResultTile extends StatelessWidget {
  const _ServiceResultTile({required this.service, required this.onTap});

  final PayService service;
  final VoidCallback onTap;

  @override
  Widget build(BuildContext context) {
    return Card(
      elevation: 0,
      margin: const EdgeInsets.only(bottom: 10),
      child: ListTile(
        contentPadding: const EdgeInsets.symmetric(horizontal: 14, vertical: 4),
        leading: ServiceIcon(service.icon, size: 44),
        title: Text(service.name, style: const TextStyle(fontWeight: FontWeight.w600)),
        subtitle: Text(payCategoryById(service.categoryId).name),
        trailing: const Icon(Icons.chevron_right),
        onTap: onTap,
      ),
    );
  }
}

class _FavoriteCard extends StatelessWidget {
  const _FavoriteCard({required this.favorite, required this.onRemove});

  final FavoritePayment favorite;
  final VoidCallback onRemove;

  @override
  Widget build(BuildContext context) {
    final service = payServiceById(favorite.serviceId);
    if (service == null) return const SizedBox.shrink();
    return SizedBox(
      width: 176,
      child: Card(
        elevation: 0,
        margin: EdgeInsets.zero,
        child: InkWell(
          borderRadius: BorderRadius.circular(12),
          onTap: () => context.push(
            Routes.payForm,
            extra: PayFormArgs(
              service: service,
              account: favorite.account,
              amountTiyin: favorite.amountTiyin,
            ),
          ),
          child: Padding(
            padding: const EdgeInsets.fromLTRB(12, 8, 4, 8),
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                Row(
                  children: [
                    Expanded(
                      child: Text(
                        service.name,
                        maxLines: 1,
                        overflow: TextOverflow.ellipsis,
                        style: const TextStyle(fontWeight: FontWeight.w700),
                      ),
                    ),
                    IconButton(
                      visualDensity: VisualDensity.compact,
                      iconSize: 18,
                      tooltip: Strings.remove,
                      onPressed: onRemove,
                      icon: const Icon(Icons.close),
                    ),
                  ],
                ),
                Text(favorite.account),
                Text(formatSom(favorite.amountTiyin), style: const TextStyle(color: AppColors.muted)),
              ],
            ),
          ),
        ),
      ),
    );
  }
}
