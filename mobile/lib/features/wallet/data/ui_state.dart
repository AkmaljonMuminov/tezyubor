import 'package:flutter_riverpod/flutter_riverpod.dart';

/// Balansni yashirish (ko'z belgisi). Faqat ilova ochiq paytida; qayta ishga tushganda ko'rinadi.
final balanceHiddenProvider = StateProvider<bool>((ref) => false);
