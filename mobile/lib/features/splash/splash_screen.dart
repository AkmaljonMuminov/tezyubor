import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:go_router/go_router.dart';

import '../../core/brand.dart';
import '../../core/router.dart';
import '../../core/theme/app_colors.dart';
import '../../shared/brand_widgets.dart';
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
    return const Scaffold(
      backgroundColor: AppColors.navyDeep,
      body: NavyBackground(
        child: Center(
          child: Column(
            mainAxisSize: MainAxisSize.min,
            children: [
              BrandLogo(size: 140),
              SizedBox(height: 24),
              Text(
                AppBrand.wordmark,
                style: TextStyle(
                  color: AppColors.silver,
                  fontSize: 34,
                  fontWeight: FontWeight.w800,
                  letterSpacing: 4,
                ),
              ),
              SizedBox(height: 8),
              Text(
                AppBrand.slogan,
                style: TextStyle(color: AppColors.goldLight, fontSize: 16, letterSpacing: 1.5),
              ),
            ],
          ),
        ),
      ),
    );
  }
}
