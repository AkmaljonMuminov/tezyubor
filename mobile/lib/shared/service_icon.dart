import 'package:flutter/material.dart';
import 'package:flutter_svg/flutter_svg.dart';

import '../core/theme/app_colors.dart';

/// Xizmat ikonkasi: SVG (matnsiz) + tema rangi + yumaloq fon. Matn alohida vidjetda beriladi (l10n uchun).
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
        color: AppColors.tint,
        borderRadius: BorderRadius.circular(size * 0.28),
      ),
      child: SvgPicture.asset(
        asset,
        colorFilter: const ColorFilter.mode(AppColors.primaryDark, BlendMode.srcIn),
      ),
    );
  }
}
