import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:go_router/go_router.dart';

import '../features/auth/presentation/otp_screen.dart';
import '../features/auth/presentation/phone_screen.dart';
import '../features/auth/presentation/pin_create_screen.dart';
import '../features/auth/presentation/pin_login_screen.dart';
import '../features/home/home_placeholder_screen.dart';
import '../features/splash/splash_screen.dart';

class Routes {
  const Routes._();
  static const splash = '/';
  static const phone = '/phone';
  static const otp = '/otp';
  static const pinCreate = '/pin-create';
  static const pinLogin = '/pin';
  static const home = '/home';
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
      GoRoute(path: Routes.home, builder: (_, __) => const HomePlaceholderScreen()),
    ],
  );
});
