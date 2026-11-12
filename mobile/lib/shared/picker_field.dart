import 'package:flutter/material.dart';

import '../core/theme/app_colors.dart';

/// Ro'yxatdan tanlash maydoni: bosilganda pastdan oyna ochiladi (hudud, ETK kabi uzun ro'yxatlar uchun).
/// [options]: kalit -> ko'rinadigan matn. [selectedKey] ro'yxatda ajratib ko'rsatiladi.
class PickerField extends StatelessWidget {
  const PickerField({
    super.key,
    required this.label,
    required this.placeholder,
    required this.options,
    required this.onSelected,
    this.selectedKey,
    this.enabled = true,
    this.errorText,
  });

  final String label;
  final String placeholder;
  final List<MapEntry<String, String>> options;
  final String? selectedKey;
  final ValueChanged<String> onSelected;
  final bool enabled;
  final String? errorText;

  String? get _valueText {
    for (final o in options) {
      if (o.key == selectedKey) return o.value;
    }
    return null;
  }

  Future<void> _open(BuildContext context) async {
    final picked = await showModalBottomSheet<String>(
      context: context,
      showDragHandle: true,
      isScrollControlled: true,
      builder: (ctx) => SafeArea(
        child: ConstrainedBox(
          constraints: BoxConstraints(maxHeight: MediaQuery.sizeOf(ctx).height * 0.7),
          child: ListView(
            shrinkWrap: true,
            padding: const EdgeInsets.only(bottom: 12),
            children: [
              for (final o in options)
                ListTile(
                  title: Text(
                    o.value,
                    style: TextStyle(
                      color: o.key == selectedKey ? AppColors.primaryDark : AppColors.text,
                      fontWeight: o.key == selectedKey ? FontWeight.w700 : FontWeight.w400,
                    ),
                  ),
                  trailing: o.key == selectedKey ? const Icon(Icons.check, color: AppColors.primary) : null,
                  onTap: () => Navigator.of(ctx).pop(o.key),
                ),
            ],
          ),
        ),
      ),
    );
    if (picked != null) onSelected(picked);
  }

  @override
  Widget build(BuildContext context) {
    final text = _valueText;
    return Column(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        Padding(
          padding: const EdgeInsets.only(bottom: 6),
          child: Text(label, style: const TextStyle(color: AppColors.muted)),
        ),
        InkWell(
          borderRadius: BorderRadius.circular(14),
          onTap: enabled ? () => _open(context) : null,
          child: Container(
            padding: const EdgeInsets.symmetric(horizontal: 16, vertical: 16),
            decoration: BoxDecoration(
              color: AppColors.surface,
              borderRadius: BorderRadius.circular(14),
              border: errorText == null ? null : Border.all(color: AppColors.error),
            ),
            child: Row(
              children: [
                Expanded(
                  child: Text(
                    text ?? placeholder,
                    style: TextStyle(
                      fontSize: 16,
                      color: text == null ? AppColors.muted : AppColors.text,
                    ),
                  ),
                ),
                Icon(Icons.keyboard_arrow_down, color: enabled ? AppColors.primary : AppColors.muted),
              ],
            ),
          ),
        ),
        if (errorText != null)
          Padding(
            padding: const EdgeInsets.only(top: 4, left: 4),
            child: Text(errorText!, style: const TextStyle(color: AppColors.error, fontSize: 12)),
          ),
      ],
    );
  }
}
