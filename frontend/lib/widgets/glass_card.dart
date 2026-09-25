import 'package:flutter/material.dart';
import '../theme/app_theme.dart';

/// A card with a subtle glass-like border and surface colour.
class GlassCard extends StatelessWidget {
  final Widget child;
  final EdgeInsetsGeometry? padding;
  final double radius;
  final Color? borderColor;
  final Color? backgroundColor;
  final List<BoxShadow>? shadows;

  const GlassCard({
    super.key,
    required this.child,
    this.padding = const EdgeInsets.all(20),
    this.radius = 20,
    this.borderColor,
    this.backgroundColor,
    this.shadows,
  });

  @override
  Widget build(BuildContext context) => Container(
    padding: padding,
    decoration: BoxDecoration(
      color: backgroundColor ?? AppTheme.surface,
      borderRadius: BorderRadius.circular(radius),
      border: Border.all(color: borderColor ?? AppTheme.border),
      boxShadow: shadows,
    ),
    child: child,
  );
}
