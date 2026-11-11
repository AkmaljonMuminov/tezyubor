import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:flutter_svg/flutter_svg.dart';
import 'package:go_router/go_router.dart';

import '../../core/assets.dart';
import '../../core/brand.dart';
import '../../core/router.dart';
import '../../core/theme/app_colors.dart';
import '../auth/data/auth_repository.dart';

class SplashScreen extends ConsumerStatefulWidget {
  const SplashScreen({super.key});

  @override
  ConsumerState<SplashScreen> createState() => _SplashScreenState();
}

class _SplashScreenState extends ConsumerState<SplashScreen> {
  @override
  void initState() {
    super.initState();
    Future<void>.delayed(const Duration(milliseconds: 1200), _next);
  }

  Future<void> _next() async {
    final hasPin = await ref.read(authRepositoryProvider).hasPin();
    if (!mounted) return;
    context.go(hasPin ? Routes.pinLogin : Routes.phone);
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      backgroundColor: AppColors.primary,
      body: Center(
        child: Column(
          mainAxisSize: MainAxisSize.min,
          children: [
            SvgPicture.asset(AppAssets.splashMark, width: 120, height: 120),
            const SizedBox(height: 28),
            const Text(
              AppBrand.name,
              style: TextStyle(color: Colors.white, fontSize: 40, fontWeight: FontWeight.w800),
            ),
            const SizedBox(height: 8),
            const Text(
              AppBrand.tagline,
              style: TextStyle(color: Color(0xFFE9FFF0), fontSize: 16),
            ),
          ],
        ),
      ),
    );
  }
}
