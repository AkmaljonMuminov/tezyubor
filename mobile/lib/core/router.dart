import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:go_router/go_router.dart';

import '../features/auth/presentation/otp_screen.dart';
import '../features/auth/presentation/phone_screen.dart';
import '../features/auth/presentation/pin_create_screen.dart';
import '../features/auth/presentation/pin_login_screen.dart';
import '../features/home/home_screen.dart';
import '../features/profile/profile_screen.dart';
import '../features/splash/splash_screen.dart';
import '../features/wallet/domain/wallet_models.dart';
import '../features/wallet/presentation/monitoring_screen.dart';
import '../features/wallet/presentation/own_transfer_screen.dart';
import '../features/wallet/presentation/pay_hub_screen.dart';
import '../features/wallet/presentation/pay_screen.dart';
import '../features/wallet/presentation/receipt_screen.dart';
import '../features/wallet/presentation/transfer_screen.dart';
import '../features/wallet/presentation/transfers_screen.dart';
import '../shared/main_shell.dart';

class Routes {
  const Routes._();
  static const splash = '/';
  static const phone = '/phone';
  static const otp = '/otp';
  static const pinCreate = '/pin-create';
  static const pinLogin = '/pin';

  // Pastki navigatsiya bo'limlari
  static const home = '/home';
  static const transfers = '/transfers';
  static const payHub = '/pay-hub';
  static const monitoring = '/monitoring';
  static const profile = '/profile';

  // Bo'limlar ustidan ochiladigan ekranlar
  static const transfer = '/transfer';
  static const transferOwn = '/transfer-own';
  static const pay = '/pay';
  static const payForm = '/pay-form';
  static const result = '/result';
  static const receipt = '/receipt';
}

/// OTP ekraniga beriladigan argumentlar.
class OtpArgs {
  const OtpArgs({required this.challengeId, required this.phone});
  final String challengeId;
  final String phone;
}

final routerProvider = Provider<GoRouter>((ref) {
  return GoRouter(
    initialLocation: Routes.splash,
    routes: [
      GoRoute(path: Routes.splash, builder: (_, __) => const SplashScreen()),
      GoRoute(path: Routes.phone, builder: (_, __) => const PhoneScreen()),
      GoRoute(
        path: Routes.otp,
        builder: (_, state) => OtpScreen(args: state.extra! as OtpArgs),
      ),
      GoRoute(path: Routes.pinCreate, builder: (_, __) => const PinCreateScreen()),
      GoRoute(path: Routes.pinLogin, builder: (_, __) => const PinLoginScreen()),

      StatefulShellRoute.indexedStack(
        builder: (_, __, shell) => MainShell(navigationShell: shell),
        branches: [
          StatefulShellBranch(routes: [
            GoRoute(path: Routes.home, builder: (_, __) => const HomeScreen()),
          ]),
          StatefulShellBranch(routes: [
            GoRoute(path: Routes.transfers, builder: (_, __) => const TransfersScreen()),
          ]),
          StatefulShellBranch(routes: [
            GoRoute(path: Routes.payHub, builder: (_, __) => const PayHubScreen()),
          ]),
          StatefulShellBranch(routes: [
            GoRoute(path: Routes.monitoring, builder: (_, __) => const MonitoringScreen()),
          ]),
          StatefulShellBranch(routes: [
            GoRoute(path: Routes.profile, builder: (_, __) => const ProfileScreen()),
          ]),
        ],
      ),

      GoRoute(
        path: Routes.transfer,
        // `extra` — oldindan to'ldiriladigan karta raqami (so'nggi qabul qiluvchidan), bo'lmasligi ham mumkin.
        builder: (_, state) => TransferScreen(initialCard: state.extra as String?),
      ),
      GoRoute(path: Routes.transferOwn, builder: (_, __) => const OwnTransferScreen()),
      GoRoute(
        path: Routes.pay,
        builder: (_, state) => PayScreen(category: state.extra! as PayCategory),
      ),
      GoRoute(
        path: Routes.payForm,
        builder: (_, state) => PayFormScreen(args: state.extra! as PayFormArgs),
      ),
      GoRoute(
        path: Routes.result,
        builder: (_, state) => ReceiptScreen(txn: state.extra! as Txn, fresh: true),
      ),
      GoRoute(
        path: Routes.receipt,
        builder: (_, state) => ReceiptScreen(txn: state.extra! as Txn),
      ),
    ],
  );
});
