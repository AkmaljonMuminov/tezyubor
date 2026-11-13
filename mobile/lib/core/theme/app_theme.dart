import 'package:flutter/material.dart';

import 'app_colors.dart';

class AppTheme {
  const AppTheme._();

  static ThemeData light() {
    final scheme = ColorScheme.fromSeed(
      seedColor: AppColors.royal,
      primary: AppColors.primary,
      secondary: AppColors.gold,
      error: AppColors.error,
      surface: AppColors.surface,
    );
    return ThemeData(
      useMaterial3: true,
      colorScheme: scheme,
      scaffoldBackgroundColor: AppColors.background,
      textTheme: Typography.blackMountainView.apply(
        bodyColor: AppColors.text,
        displayColor: AppColors.text,
      ),
      appBarTheme: const AppBarTheme(
        backgroundColor: Colors.transparent,
        surfaceTintColor: Colors.transparent,
        foregroundColor: AppColors.text,
        elevation: 0,
      ),
      progressIndicatorTheme: const ProgressIndicatorThemeData(color: AppColors.primary),
      inputDecorationTheme: InputDecorationTheme(
        filled: true,
        fillColor: AppColors.surface,
        border: OutlineInputBorder(
          borderRadius: BorderRadius.circular(14),
          borderSide: BorderSide.none,
        ),
        // Fokus — cyan (dizayn tizimi: "cyan for focus/active states").
        focusedBorder: OutlineInputBorder(
          borderRadius: BorderRadius.circular(14),
          borderSide: const BorderSide(color: AppColors.cyan, width: 2),
        ),
      ),
      filledButtonTheme: FilledButtonThemeData(
        style: FilledButton.styleFrom(
          minimumSize: const Size.fromHeight(56),
          shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(18)),
          textStyle: const TextStyle(fontSize: 17, fontWeight: FontWeight.w700),
        ),
      ),
      navigationBarTheme: NavigationBarThemeData(
        backgroundColor: AppColors.navy,
        surfaceTintColor: Colors.transparent,
        indicatorColor: AppColors.royalSoft,
        labelTextStyle: WidgetStateProperty.resolveWith((states) {
          final selected = states.contains(WidgetState.selected);
          return TextStyle(
            fontSize: 12,
            fontWeight: selected ? FontWeight.w700 : FontWeight.w500,
            color: selected ? AppColors.goldLight : AppColors.paleBlueDim,
          );
        }),
      ),
    );
  }
}
