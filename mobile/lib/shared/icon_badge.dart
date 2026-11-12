import 'package:flutter/material.dart';

import '../core/theme/app_colors.dart';

/// [ServiceIcon] ning Material ikonka varianti: yumaloq och-yashil fon.
class IconBadge extends StatelessWidget {
  const IconBadge(this.icon, {super.key, this.size = 48});

  final IconData icon;
  final double size;

  @override
  Widget build(BuildContext context) {
    return Container(
      width: size,
      height: size,
      decoration: BoxDecoration(
        color: AppColors.tint,
        borderRadius: BorderRadius.circular(size * 0.28),
      ),
      child: Icon(icon, color: AppColors.primaryDark, size: size * 0.5),
    );
  }
}
