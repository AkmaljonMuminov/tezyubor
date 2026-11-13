import 'package:flutter/material.dart';

import '../core/theme/app_colors.dart';

/// [ServiceIcon] ning Material ikonka varianti: navy yumaloq fon, oltin ikonka.
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
        gradient: const LinearGradient(
          begin: Alignment.topLeft,
          end: Alignment.bottomRight,
          colors: [AppColors.navyMid, AppColors.navy],
        ),
        borderRadius: BorderRadius.circular(size * 0.28),
        border: Border.all(color: AppColors.cyanLine),
      ),
      child: Icon(icon, color: AppColors.goldLight, size: size * 0.5),
    );
  }
}
