import 'package:flutter/material.dart';
import 'package:flutter_svg/flutter_svg.dart';
import 'package:go_router/go_router.dart';

import '../core/assets.dart';
import '../core/l10n/strings.dart';
import '../core/theme/app_colors.dart';

/// Pastki navigatsiya: Asosiy, O'tkazmalar, To'lov, Monitoring, Profil.
/// Har bo'limning o'z navigatsiya tarixi saqlanadi (`StatefulShellRoute`).
/// Navy panel: faol ikonka oltin gradient, nofaol — och ko'k (dizayn tizimi).
class MainShell extends StatelessWidget {
  const MainShell({super.key, required this.navigationShell});

  final StatefulNavigationShell navigationShell;

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      body: navigationShell,
      bottomNavigationBar: NavigationBar(
        selectedIndex: navigationShell.currentIndex,
        labelBehavior: NavigationDestinationLabelBehavior.alwaysShow,
        onDestinationSelected: (i) => navigationShell.goBranch(
          i,
          // Joriy bo'limni qayta bosganda uning boshiga qaytadi.
          initialLocation: i == navigationShell.currentIndex,
        ),
        destinations: const [
          NavigationDestination(
            icon: _NavIcon(AppAssets.icHome),
            selectedIcon: _NavIcon(AppAssets.icHome, selected: true),
            label: Strings.navHome,
          ),
          NavigationDestination(
            icon: _NavIcon(AppAssets.icTransfer),
            selectedIcon: _NavIcon(AppAssets.icTransfer, selected: true),
            label: Strings.navTransfers,
          ),
          NavigationDestination(
            icon: _NavIcon(AppAssets.icPayments),
            selectedIcon: _NavIcon(AppAssets.icPayments, selected: true),
            label: Strings.navPay,
          ),
          NavigationDestination(
            icon: _NavIcon(AppAssets.icAnalytics),
            selectedIcon: _NavIcon(AppAssets.icAnalytics, selected: true),
            label: Strings.navMonitoring,
          ),
          NavigationDestination(
            icon: _NavIcon(AppAssets.icProfile),
            selectedIcon: _NavIcon(AppAssets.icProfile, selected: true),
            label: Strings.navProfile,
          ),
        ],
      ),
    );
  }
}

class _NavIcon extends StatelessWidget {
  const _NavIcon(this.asset, {this.selected = false});

  final String asset;
  final bool selected;

  @override
  Widget build(BuildContext context) {
    return SvgPicture.asset(
      asset,
      width: 26,
      height: 26,
      // Nofaol holatda bitta och rang; faol holatda SVG'dagi oltin gradient.
      colorFilter: selected ? null : const ColorFilter.mode(AppColors.paleBlueDim, BlendMode.srcIn),
    );
  }
}
