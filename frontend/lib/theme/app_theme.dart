import 'package:flutter/material.dart';
import 'package:flutter/services.dart';
import 'package:google_fonts/google_fonts.dart';

class AppTheme {
  // ── Tech-forward neon palette ───────────────────────────────────────────────
  // Surfaces — deep navy blacks with a subtle blue undertone
  static const background   = Color(0xFF080C14);   // near-black navy
  static const surface      = Color(0xFF0E1420);   // dark navy card
  static const surfaceHigh  = Color(0xFF151D2E);   // lifted card
  static const surfaceAlt   = Color(0xFF1C2640);   // subtle highlight

  // Brand — electric cyan-blue as the hero accent
  static const primary      = Color(0xFF00D4FF);   // electric cyan
  static const primaryDim   = Color(0xFF0099CC);   // dimmed for borders
  static const primaryLight = Color(0xFF66E8FF);   // light glow variant

  // Secondary — hot magenta pop of fun
  static const magenta      = Color(0xFFFF2D78);   // hot pink/magenta
  static const magentaDim   = Color(0xFFCC2460);

  // Tertiary — acid lime for "clean/safe" signals
  static const lime         = Color(0xFF39FF14);   // neon lime
  static const limeDim      = Color(0xFF2ACC0F);

  // Supporting
  static const amber        = Color(0xFFFFB800);   // warm amber warning
  static const violet       = Color(0xFFBF5FFF);   // violet for document flow
  static const violetDim    = Color(0xFF8A3FCC);

  // Semantic
  static const success      = Color(0xFF00E676);   // neon green
  static const warning      = Color(0xFFFFB800);   // amber
  static const danger       = Color(0xFFFF3D57);   // red-pink

  // Text
  static const text         = Color(0xFFE8F4FF);   // cool white
  static const textSub      = Color(0xFF8BA3C4);   // steel blue-grey
  static const muted        = Color(0xFF3D5070);   // dark muted

  // Structure
  static const border       = Color(0xFF1A2E4A);   // dark navy border
  static const borderHigh   = Color(0xFF254066);   // brighter border
  static const borderNeon   = Color(0xFF00D4FF);   // neon border on focus

  // ── Gradients ──────────────────────────────────────────────────────────────

  /// Hero banner — deep navy → electric cyan
  static const heroGradient = LinearGradient(
    begin: Alignment.topLeft,
    end: Alignment.bottomRight,
    colors: [Color(0xFF0A1628), Color(0xFF003D5C), Color(0xFF006080)],
    stops: [0.0, 0.55, 1.0],
  );

  /// Brand logo — cyan → magenta (fun diagonal)
  static const brandGradient = LinearGradient(
    begin: Alignment.topLeft,
    end: Alignment.bottomRight,
    colors: [Color(0xFF00D4FF), Color(0xFFBF5FFF), Color(0xFFFF2D78)],
    stops: [0.0, 0.55, 1.0],
  );

  /// Image analysis card — violet → magenta
  static const imageGradient = LinearGradient(
    begin: Alignment.topLeft,
    end: Alignment.bottomRight,
    colors: [Color(0xFF4A1A8A), Color(0xFFBF5FFF)],
  );

  /// Document Verification card — teal-cyan
  static const docGradient = LinearGradient(
    begin: Alignment.topLeft,
    end: Alignment.bottomRight,
    colors: [Color(0xFF004466), Color(0xFF00D4FF)],
  );

  /// Neon glow used on progress bars & active rings
  static const neonGradient = LinearGradient(
    colors: [Color(0xFF00D4FF), Color(0xFF39FF14)],
  );

  // ── Theme ──────────────────────────────────────────────────────────────────
  static ThemeData dark() {
    final base = GoogleFonts.spaceGroteskTextTheme(         // techy geometric font
      const TextTheme(
        displaySmall: TextStyle(
          fontSize: 32,
          fontWeight: FontWeight.w700,
          letterSpacing: -1.0,
          color: text,
        ),
        headlineLarge: TextStyle(
          fontSize: 28,
          fontWeight: FontWeight.w700,
          letterSpacing: -0.6,
          color: text,
        ),
        headlineMedium: TextStyle(
          fontSize: 22,
          fontWeight: FontWeight.w700,
          letterSpacing: -0.4,
          color: text,
        ),
        headlineSmall: TextStyle(
          fontSize: 18,
          fontWeight: FontWeight.w700,
          color: text,
        ),
        titleLarge: TextStyle(
          fontSize: 16,
          fontWeight: FontWeight.w700,
          color: text,
        ),
        titleMedium: TextStyle(
          fontSize: 14,
          fontWeight: FontWeight.w600,
          color: text,
        ),
        bodyLarge: TextStyle(fontSize: 15, height: 1.6, color: textSub),
        bodyMedium: TextStyle(fontSize: 13, height: 1.5, color: textSub),
        labelLarge: TextStyle(
          fontSize: 13,
          fontWeight: FontWeight.w700,
          letterSpacing: 0.3,
          color: text,
        ),
        labelSmall: TextStyle(
          fontSize: 10,
          fontWeight: FontWeight.w600,
          letterSpacing: 1.0,
          color: muted,
        ),
      ),
    );

    final scheme = ColorScheme.fromSeed(
      seedColor: primary,
      brightness: Brightness.dark,
      surface: surface,
      primary: primary,
      secondary: violet,
      tertiary: magenta,
      onSurface: text,
      onPrimary: background,
    ).copyWith(
      surfaceContainerHighest: surfaceHigh,
      outline: border,
    );

    return ThemeData(
      useMaterial3: true,
      brightness: Brightness.dark,
      colorScheme: scheme,
      scaffoldBackgroundColor: background,
      textTheme: base,
      appBarTheme: AppBarTheme(
        backgroundColor: background,
        foregroundColor: text,
        elevation: 0,
        scrolledUnderElevation: 0,
        systemOverlayStyle: const SystemUiOverlayStyle(
          statusBarColor: Colors.transparent,
          statusBarIconBrightness: Brightness.light,
          systemNavigationBarColor: surface,
          systemNavigationBarIconBrightness: Brightness.light,
        ),
        titleTextStyle: GoogleFonts.spaceGrotesk(
          fontSize: 17,
          fontWeight: FontWeight.w700,
          color: text,
        ),
        iconTheme: const IconThemeData(color: textSub),
      ),
      cardTheme: CardThemeData(
        color: surface,
        elevation: 0,
        margin: EdgeInsets.zero,
        shape: RoundedRectangleBorder(
          borderRadius: BorderRadius.circular(20),
          side: const BorderSide(color: border),
        ),
      ),
      inputDecorationTheme: InputDecorationTheme(
        filled: true,
        fillColor: surfaceHigh,
        hintStyle: const TextStyle(color: muted, fontSize: 13),
        border: OutlineInputBorder(
          borderRadius: BorderRadius.circular(14),
          borderSide: const BorderSide(color: border),
        ),
        enabledBorder: OutlineInputBorder(
          borderRadius: BorderRadius.circular(14),
          borderSide: const BorderSide(color: border),
        ),
        focusedBorder: OutlineInputBorder(
          borderRadius: BorderRadius.circular(14),
          borderSide: const BorderSide(color: primary, width: 1.5),
        ),
        contentPadding: const EdgeInsets.symmetric(horizontal: 16, vertical: 14),
      ),
      filledButtonTheme: FilledButtonThemeData(
        style: FilledButton.styleFrom(
          backgroundColor: primary,
          foregroundColor: background,
          textStyle: GoogleFonts.spaceGrotesk(
            fontSize: 14,
            fontWeight: FontWeight.w700,
          ),
          shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(14)),
          padding: const EdgeInsets.symmetric(horizontal: 24, vertical: 16),
          elevation: 0,
        ),
      ),
      outlinedButtonTheme: OutlinedButtonThemeData(
        style: OutlinedButton.styleFrom(
          foregroundColor: text,
          side: const BorderSide(color: border),
          shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(14)),
          padding: const EdgeInsets.symmetric(horizontal: 24, vertical: 16),
          textStyle: GoogleFonts.spaceGrotesk(
            fontSize: 14,
            fontWeight: FontWeight.w600,
          ),
        ),
      ),
      navigationBarTheme: NavigationBarThemeData(
        backgroundColor: surface,
        indicatorColor: primary.withValues(alpha: .12),
        indicatorShape: RoundedRectangleBorder(
          borderRadius: BorderRadius.circular(12),
        ),
        elevation: 0,
        height: 68,
        labelBehavior: NavigationDestinationLabelBehavior.alwaysShow,
        labelTextStyle: WidgetStateProperty.resolveWith((states) {
          final selected = states.contains(WidgetState.selected);
          return GoogleFonts.spaceGrotesk(
            fontSize: 10,
            fontWeight: FontWeight.w700,
            color: selected ? primary : muted,
          );
        }),
        iconTheme: WidgetStateProperty.resolveWith((states) {
          final selected = states.contains(WidgetState.selected);
          return IconThemeData(
            color: selected ? primary : muted,
            size: 22,
          );
        }),
      ),
      dividerTheme: const DividerThemeData(
        color: border,
        thickness: 1,
        space: 1,
      ),
      listTileTheme: const ListTileThemeData(
        tileColor: Colors.transparent,
        contentPadding: EdgeInsets.symmetric(horizontal: 0),
      ),
      iconTheme: const IconThemeData(color: textSub, size: 22),
      progressIndicatorTheme: const ProgressIndicatorThemeData(
        color: primary,
        linearTrackColor: surfaceAlt,
        circularTrackColor: surfaceAlt,
      ),
      chipTheme: ChipThemeData(
        backgroundColor: surfaceHigh,
        side: const BorderSide(color: border),
        labelStyle: GoogleFonts.spaceGrotesk(
          fontSize: 11,
          fontWeight: FontWeight.w600,
          color: textSub,
        ),
        padding: const EdgeInsets.symmetric(horizontal: 10, vertical: 6),
        shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(8)),
      ),
    );
  }
}
