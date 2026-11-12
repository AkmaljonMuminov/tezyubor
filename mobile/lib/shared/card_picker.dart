import 'package:flutter/material.dart';

import '../core/money.dart';
import '../core/theme/app_colors.dart';
import '../features/wallet/domain/wallet_models.dart';

/// Karta tanlash: har karta alohida bosiladigan qator.
class CardPicker extends StatelessWidget {
  const CardPicker({
    super.key,
    required this.cards,
    required this.selectedId,
    required this.onChanged,
  });

  final List<CardInfo> cards;
  final String? selectedId;
  final ValueChanged<String> onChanged;

  @override
  Widget build(BuildContext context) {
    return Column(
      children: [
        for (final c in cards)
          Padding(
            padding: const EdgeInsets.only(bottom: 8),
            child: InkWell(
              borderRadius: BorderRadius.circular(14),
              onTap: () => onChanged(c.id),
              child: Container(
                padding: const EdgeInsets.all(14),
                decoration: BoxDecoration(
                  color: AppColors.surface,
                  borderRadius: BorderRadius.circular(14),
                  border: Border.all(
                    color: c.id == selectedId ? AppColors.primary : Colors.transparent,
                    width: 2,
                  ),
                ),
                child: Row(
                  children: [
                    Expanded(
                      child: Column(
                        crossAxisAlignment: CrossAxisAlignment.start,
                        children: [
                          Text('${c.network} ${c.masked}',
                              style: const TextStyle(fontWeight: FontWeight.w700)),
                          const SizedBox(height: 2),
                          Text(formatSom(c.balanceTiyin),
                              style: const TextStyle(color: AppColors.muted)),
                        ],
                      ),
                    ),
                    if (c.id == selectedId)
                      const Icon(Icons.check_circle, color: AppColors.primary),
                  ],
                ),
              ),
            ),
          ),
      ],
    );
  }
}
