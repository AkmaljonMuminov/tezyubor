import 'package:flutter/material.dart';
import 'package:go_router/go_router.dart';

import '../core/l10n/strings.dart';

/// Pastki navigatsiya: Asosiy, O'tkazmalar, To'lov, Monitoring, Profil.
/// Har bo'limning o'z navigatsiya tarixi saqlanadi (`StatefulShellRoute`).
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
          NavigationDestination(icon: Icon(Icons.home_outlined), selectedIcon: Icon(Icons.home), label: Strings.navHome),
          NavigationDestination(
              icon: Icon(Icons.swap_horiz), selectedIcon: Icon(Icons.swap_horiz), label: Strings.navTransfers),
          NavigationDestination(
              icon: Icon(Icons.account_balance_wallet_outlined),
              selectedIcon: Icon(Icons.account_balance_wallet),
              label: Strings.navPay),
          NavigationDestination(icon: Icon(Icons.history), selectedIcon: Icon(Icons.history), label: Strings.navMonitoring),
          NavigationDestination(
              icon: Icon(Icons.person_outline), selectedIcon: Icon(Icons.person), label: Strings.navProfile),
        ],
      ),
    );
  }
}
