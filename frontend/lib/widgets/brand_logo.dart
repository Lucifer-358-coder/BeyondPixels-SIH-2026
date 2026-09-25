import 'package:flutter/material.dart';
import '../theme/app_theme.dart';

/// Cropped directly from the user's BeyondPixels PDF logo. Never use the team logo.
class BrandLogo extends StatelessWidget {
  final double size;
  const BrandLogo({super.key, required this.size});

  @override
  Widget build(BuildContext context) => Container(
    width: size,
    height: size,
    decoration: BoxDecoration(
      borderRadius: BorderRadius.circular(size * .24),
      color: AppTheme.surface,
      boxShadow: [BoxShadow(color: AppTheme.primary.withValues(alpha: .2), blurRadius: 9)],
    ),
    clipBehavior: Clip.antiAlias,
    child: Image.asset('assets/branding/beyondpixels_icon.png', fit: BoxFit.cover),
  );
}
