import 'package:flutter/material.dart';
import 'package:flutter_svg/flutter_svg.dart';

import '../core/theme/app_colors.dart';

/// Xizmat ikonkasi: oltin gradientli SVG (matnsiz) navy yumaloq fonda. Matn alohida vidjetda beriladi (l10n uchun).
class ServiceIcon extends StatelessWidget {
  const ServiceIcon(this.asset, {super.key, this.size = 56});

  final String asset;
  final double size;

  @override
  Widget build(BuildContext context) {
    return Container(
      width: size,
      height: size,
      padding: EdgeInsets.all(size * 0.2),
      decoration: BoxDecoration(
        gradient: const LinearGradient(
          begin: Alignment.topLeft,
          end: Alignment.bottomRight,
          colors: [AppColors.navyMid, AppColors.navy],
        ),
        borderRadius: BorderRadius.circular(size * 0.28),
        border: Border.all(color: AppColors.cyanLine),
      ),
      child: SvgPicture.asset(asset),
    );
  }
}
