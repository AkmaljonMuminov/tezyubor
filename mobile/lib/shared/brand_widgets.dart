import 'package:flutter/material.dart';
import 'package:flutter_svg/flutter_svg.dart';

import '../core/assets.dart';
import '../core/brand.dart';
import '../core/theme/app_colors.dart';
import 'test_mode_banner.dart';

/// ORVEX PAY logotipi (logo_mark).
class BrandLogo extends StatelessWidget {
  const BrandLogo({super.key, this.size = 96});

  final double size;

  @override
  Widget build(BuildContext context) {
    return Image.asset(
      AppAssets.logo,
      width: size,
      height: size,
      filterQuality: FilterQuality.medium,
      semanticLabel: AppBrand.name,
    );
  }
}

/// Midnight navy gradient fon (standart: premium_navy.svg). [child] o'lchamni belgilaydi; Scaffold ichida butun ekranni to'ldiradi.
class NavyBackground extends StatelessWidget {
  const NavyBackground({super.key, this.child, this.asset = AppAssets.bgNavy});

  final Widget? child;
  final String asset;

  @override
  Widget build(BuildContext context) {
    return Stack(
      children: [
        Positioned.fill(child: SvgPicture.asset(asset, fit: BoxFit.cover)),
        if (child != null) child!,
      ],
    );
  }
}

/// Kirish ekranlari tepasidagi navy sarlavha: logotip + nom + shior.
/// Klaviatura ochiq bo'lsa ixcham ko'rinishga o'tadi (kichik ekranda forma sig'ishi uchun).
class AuthHeader extends StatelessWidget {
  const AuthHeader({super.key});

  @override
  Widget build(BuildContext context) {
    final compact = MediaQuery.of(context).viewInsets.bottom > 0;
    return ClipRRect(
      borderRadius: const BorderRadius.vertical(bottom: Radius.circular(28)),
      child: SizedBox(
        width: double.infinity,
        child: NavyBackground(
          child: SafeArea(
            bottom: false,
            child: Column(
              mainAxisSize: MainAxisSize.min,
              children: [
                const TestModeBanner(),
                SizedBox(height: compact ? 10 : 20),
                BrandLogo(size: compact ? 48 : 84),
                SizedBox(height: compact ? 6 : 10),
                const Text(
                  AppBrand.wordmark,
                  style: TextStyle(
                    color: AppColors.silver,
                    fontSize: 24,
                    fontWeight: FontWeight.w800,
                    letterSpacing: 3,
                  ),
                ),
                if (!compact) ...const [
                  SizedBox(height: 4),
                  Text(
                    AppBrand.slogan,
                    style: TextStyle(color: AppColors.cyan, fontSize: 13, letterSpacing: 1),
                  ),
                ],
                SizedBox(height: compact ? 12 : 22),
              ],
            ),
          ),
        ),
      ),
    );
  }
}

/// Reklama banneri: SVG fon (matnsiz) + vidjetdagi matn. Matn Flutter'da chiziladi (SVG matn qo'llab-quvvatlanmaydi).
class PromoBanner extends StatelessWidget {
  const PromoBanner({
    super.key,
    required this.asset,
    required this.eyebrow,
    required this.title,
    required this.subtitle,
  });

  final String asset;
  final String eyebrow;
  final String title;
  final String subtitle;

  @override
  Widget build(BuildContext context) {
    return ClipRRect(
      borderRadius: BorderRadius.circular(22),
      child: AspectRatio(
        aspectRatio: 1200 / 420,
        child: Stack(
          fit: StackFit.expand,
          children: [
            SvgPicture.asset(asset, fit: BoxFit.cover),
            Padding(
              padding: const EdgeInsets.symmetric(horizontal: 18),
              child: Align(
                alignment: Alignment.centerLeft,
                child: FractionallySizedBox(
                  widthFactor: 0.62,
                  child: Column(
                    mainAxisSize: MainAxisSize.min,
                    crossAxisAlignment: CrossAxisAlignment.start,
                    children: [
                      Text(
                        eyebrow,
                        style: const TextStyle(
                          color: AppColors.goldLight,
                          fontSize: 11,
                          fontWeight: FontWeight.w700,
                          letterSpacing: 2,
                        ),
                      ),
                      const SizedBox(height: 4),
                      Text(
                        title,
                        style: const TextStyle(color: Colors.white, fontSize: 20, fontWeight: FontWeight.w800),
                      ),
                      const SizedBox(height: 2),
                      Text(subtitle, style: const TextStyle(color: AppColors.paleBlue, fontSize: 13)),
                    ],
                  ),
                ),
              ),
            ),
          ],
        ),
      ),
    );
  }
}
