import 'package:flutter/material.dart';

import '../core/l10n/strings.dart';
import '../core/theme/app_colors.dart';

/// Pul operatsiyasini bajarishdan oldin tasdiqlash oynasi. `true` — foydalanuvchi tasdiqladi.
Future<bool> showConfirmSheet(
  BuildContext context, {
  required String title,
  required List<MapEntry<String, String>> rows,
}) async {
  final ok = await showModalBottomSheet<bool>(
    context: context,
    showDragHandle: true,
    builder: (ctx) => SafeArea(
      child: Padding(
        padding: const EdgeInsets.fromLTRB(24, 0, 24, 16),
        child: Column(
          mainAxisSize: MainAxisSize.min,
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            Text(title, style: Theme.of(ctx).textTheme.titleLarge),
            const SizedBox(height: 16),
            for (final r in rows)
              Padding(
                padding: const EdgeInsets.symmetric(vertical: 6),
                child: Row(
                  mainAxisAlignment: MainAxisAlignment.spaceBetween,
                  children: [
                    Text(r.key, style: const TextStyle(color: AppColors.muted)),
                    const SizedBox(width: 12),
                    Flexible(
                      child: Text(
                        r.value,
                        textAlign: TextAlign.right,
                        style: const TextStyle(fontWeight: FontWeight.w700),
                      ),
                    ),
                  ],
                ),
              ),
            const SizedBox(height: 20),
            FilledButton(
              onPressed: () => Navigator.of(ctx).pop(true),
              child: const Text(Strings.confirm),
            ),
            const SizedBox(height: 8),
            TextButton(
              onPressed: () => Navigator.of(ctx).pop(false),
              child: const Text(Strings.cancel),
            ),
          ],
        ),
      ),
    ),
  );
  return ok ?? false;
}
