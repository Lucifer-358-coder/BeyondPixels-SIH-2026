import 'dart:async';
import '../models/session_history.dart';
import 'package:flutter/material.dart';
import '../theme/app_theme.dart';
import '../widgets/brand_logo.dart';
import '../widgets/glass_card.dart';
import '../widgets/section_header.dart';
import 'analyze_screen.dart';

class HomeScreen extends StatefulWidget {
  const HomeScreen({super.key});

  @override
  State<HomeScreen> createState() => _HomeScreenState();
}

class _HomeScreenState extends State<HomeScreen>
    with SingleTickerProviderStateMixin {
  Timer? _heroStartTimer;
  late final AnimationController _heroCtrl;
  late final Animation<double> _heroFade;
  late final Animation<Offset> _heroSlide;

  @override
  void initState() {
    super.initState();
    _heroCtrl = AnimationController(
      vsync: this,
      duration: const Duration(milliseconds: 700),
    );
    _heroFade = CurvedAnimation(parent: _heroCtrl, curve: Curves.easeOut);
    _heroSlide = Tween<Offset>(
      begin: const Offset(0, 0.08),
      end: Offset.zero,
    ).animate(CurvedAnimation(parent: _heroCtrl, curve: Curves.easeOut));
    // Stagger the entrance
    _heroStartTimer = Timer(const Duration(milliseconds: 120), () {
      if (mounted) _heroCtrl.forward();
    });
  }

  @override
  void dispose() {
    _heroStartTimer?.cancel();
    _heroCtrl.dispose();
    super.dispose();
  }


  @override
  Widget build(BuildContext context) {
    return Scaffold(
      body: SafeArea(
        child: FadeTransition(
          opacity: _heroFade,
          child: SlideTransition(
            position: _heroSlide,
            child: CustomScrollView(
              physics: const BouncingScrollPhysics(),
              slivers: [
                _buildAppBar(context),
                SliverToBoxAdapter(
                  child: Padding(
                    padding: const EdgeInsets.fromLTRB(20, 24, 20, 0),
                    child: Column(
                      crossAxisAlignment: CrossAxisAlignment.start,
                      children: [
                        _buildGreeting(context),
                        const SizedBox(height: 22),
                        _buildHeroCard(context),
                        const SizedBox(height: 30),
                        _buildStatsRow(),
                        const SizedBox(height: 30),
                        SectionHeader(
                          title: 'What to check?',

                        ),
                        const SizedBox(height: 14),
                        _buildFeatureCards(context),
                        const SizedBox(height: 30),
                        const SectionHeader(title: 'Recent analysis'),
                        const SizedBox(height: 12),
                        AnimatedBuilder(
                          animation: SessionHistory.instance,
                          builder: (context, _) {
                            final items = SessionHistory.instance.items.take(3).toList();
                            if (items.isEmpty) {
                              return const Text('No analyses yet in this session.',
                                  style: TextStyle(color: AppTheme.textSub));
                            }
                            return Column(children: items.map((entry) => Padding(
                              padding: const EdgeInsets.only(bottom: 10),
                              child: GlassCard(child: Row(children: [
                                Icon(entry.isDocument ? Icons.badge_outlined : Icons.image_outlined,
                                    color: entry.isDocument ? AppTheme.primary : AppTheme.magenta),
                                const SizedBox(width: 12),
                                Expanded(child: Text(entry.filename,
                                    style: const TextStyle(color: AppTheme.text))),
                                Text(entry.status.replaceAll('_', ' '),
                                    style: const TextStyle(color: AppTheme.textSub, fontSize: 11)),
                              ])),
                            )).toList());
                          },
                        ),
                        const SizedBox(height: 24),
                      ],
                    ),
                  ),
                ),
              ],
            ),
          ),
        ),
      ),
    );
  }

  SliverAppBar _buildAppBar(BuildContext context) => SliverAppBar(
    floating: true,
    backgroundColor: AppTheme.background,
    titleSpacing: 20,
    title: Row(
      children: [
        const BrandLogo(size: 36),
        const SizedBox(width: 10),
        Text(
          'BeyondPixels',
          style: Theme.of(context).textTheme.titleLarge?.copyWith(
            color: AppTheme.text,
            fontWeight: FontWeight.w800,
          ),
        ),
      ],
    ),
    actions: const [
      Padding(
        padding: EdgeInsets.only(right: 18),
        child: Center(child: Icon(Icons.shield_outlined, color: AppTheme.primary)),
      ),
    ],
  );

  Widget _buildGreeting(BuildContext context) => Column(
    crossAxisAlignment: CrossAxisAlignment.start,
    children: [
      Text(
        'Welcome to BeyondPixels',
        style: Theme.of(context).textTheme.bodyMedium?.copyWith(
          color: AppTheme.textSub,
        ),
      ),
      const SizedBox(height: 4),
      Text(
        'See beyond what you see.',
        style: Theme.of(context).textTheme.headlineLarge,
      ),
    ],
  );

  Widget _buildHeroCard(BuildContext context) => Container(
    height: 184,
    decoration: BoxDecoration(
      borderRadius: BorderRadius.circular(24),
      gradient: AppTheme.heroGradient,
      border: Border.all(color: AppTheme.primary.withValues(alpha: .3), width: 1),
      boxShadow: [
        BoxShadow(
          color: AppTheme.primary.withValues(alpha: .22),
          blurRadius: 32,
          offset: const Offset(0, 10),
        ),
      ],
    ),
    child: Stack(
      clipBehavior: Clip.hardEdge,
      children: [
        // Neon glow blob — top-right
        Positioned(
          right: -20,
          top: -20,
          child: Container(
            width: 150,
            height: 150,
            decoration: BoxDecoration(
              shape: BoxShape.circle,
              gradient: RadialGradient(
                colors: [
                  AppTheme.primary.withValues(alpha: .18),
                  Colors.transparent,
                ],
              ),
            ),
          ),
        ),
        // Subtle grid dots pattern
        Positioned(
          right: 16,
          bottom: 14,
          child: Opacity(
            opacity: 0.15,
            child: Icon(Icons.grid_4x4_rounded, color: AppTheme.primary, size: 72),
          ),
        ),
        Padding(
          padding: const EdgeInsets.all(22),
          child: Row(
            children: [
              Expanded(
                child: Column(
                  crossAxisAlignment: CrossAxisAlignment.start,
                  mainAxisAlignment: MainAxisAlignment.center,
                  children: [
                    Container(
                      padding: const EdgeInsets.symmetric(horizontal: 10, vertical: 4),
                      decoration: BoxDecoration(
                        color: AppTheme.primary.withValues(alpha: .15),
                        borderRadius: BorderRadius.circular(20),
                        border: Border.all(color: AppTheme.primary.withValues(alpha: .35)),
                      ),
                      child: Text(
                        'RESEARCH DEMO',
                        style: TextStyle(
                          color: AppTheme.primaryLight,
                          fontSize: 9,
                          fontWeight: FontWeight.w700,
                          letterSpacing: 1.4,
                        ),
                      ),
                    ),
                    const SizedBox(height: 11),
                    const Text(
                      'Document Verification &\nAI Media Screening',
                      style: TextStyle(
                        color: AppTheme.text,
                        fontSize: 22,
                        fontWeight: FontWeight.w700,
                        height: 1.15,
                        letterSpacing: -0.4,
                      ),
                    ),
                    const SizedBox(height: 8),
                    Text(
                      'Detect · Analyze · Stay informed',
                      style: TextStyle(
                        color: AppTheme.primary.withValues(alpha: .85),
                        fontSize: 11.5,
                        fontWeight: FontWeight.w500,
                        letterSpacing: 0.2,
                      ),
                    ),
                  ],
                ),
              ),
              const BrandLogo(size: 78),
            ],
          ),
        ),
      ],
    ),
  );

  Widget _buildStatsRow() => AnimatedBuilder(
    animation: SessionHistory.instance,
    builder: (context, _) {
      final items = SessionHistory.instance.items;
      final docs = items.where((e) => e.isDocument).length;
      return Row(children: [
        Expanded(child: _StatMini(value: '${items.length}', label: 'This session', accent: AppTheme.primary)),
        const SizedBox(width: 10),
        Expanded(child: _StatMini(value: '$docs', label: 'Documents', accent: AppTheme.success)),
        const SizedBox(width: 10),
        Expanded(child: _StatMini(value: '${items.length - docs}', label: 'Media', accent: AppTheme.violet)),
      ]);
    },
  );

  Widget _buildFeatureCards(BuildContext context) => Row(
    children: [
      Expanded(
        child: _FeatureCard(
          title: 'Document\nVerification',
          subtitle: 'OCR · MRZ · portrait\nmanual-review evidence',
          icon: Icons.badge_outlined,
          gradient: AppTheme.docGradient,
          accentColor: AppTheme.primary,
          onTap: () => Navigator.push(
            context,
            _slideRoute(const AnalyzeScreen(kind: 'document')),
          ),
        ),
      ),
      const SizedBox(width: 12),
      Expanded(
        child: _FeatureCard(
          title: 'AI Image &\nDeepfake Detection',
          subtitle: 'AI-image screening + separate\nface-based deepfake analysis',
          icon: Icons.image_search_outlined,
          gradient: AppTheme.imageGradient,
          accentColor: AppTheme.violet,
          onTap: () => Navigator.push(
            context,
            _slideRoute(const AnalyzeScreen(kind: 'image')),
          ),
        ),
      ),
    ],
  );

  PageRouteBuilder _slideRoute(Widget page) => PageRouteBuilder(
    pageBuilder: (_, _, _) => page,
    transitionsBuilder: (_, anim, _, child) => SlideTransition(
      position: Tween<Offset>(
        begin: const Offset(1.0, 0),
        end: Offset.zero,
      ).animate(CurvedAnimation(parent: anim, curve: Curves.easeOutCubic)),
      child: child,
    ),
    transitionDuration: const Duration(milliseconds: 320),
  );
}

// ── Sub-widgets ────────────────────────────────────────────────────────────────

class _StatMini extends StatelessWidget {
  final String value;
  final String label;
  final Color accent;
  const _StatMini({required this.value, required this.label, required this.accent});

  @override
  Widget build(BuildContext context) => Container(
    padding: const EdgeInsets.symmetric(vertical: 14, horizontal: 12),
    decoration: BoxDecoration(
      color: AppTheme.surfaceHigh,
      borderRadius: BorderRadius.circular(14),
      border: Border.all(color: AppTheme.border),
    ),
    child: Column(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        Text(
          value,
          style: TextStyle(
            fontSize: 17,
            fontWeight: FontWeight.w700,
            color: accent,
          ),
        ),
        const SizedBox(height: 2),
        Text(
          label,
          style: const TextStyle(fontSize: 10, color: AppTheme.muted),
        ),
      ],
    ),
  );
}

class _FeatureCard extends StatelessWidget {
  final String title, subtitle;
  final IconData icon;
  final Gradient gradient;
  final Color accentColor;
  final VoidCallback onTap;

  const _FeatureCard({
    required this.title,
    required this.subtitle,
    required this.icon,
    required this.gradient,
    required this.accentColor,
    required this.onTap,
  });

  @override
  Widget build(BuildContext context) => GestureDetector(
    onTap: onTap,
    child: Container(
      padding: const EdgeInsets.all(18),
      decoration: BoxDecoration(
        color: AppTheme.surface,
        borderRadius: BorderRadius.circular(20),
        border: Border.all(color: AppTheme.border),
      ),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Container(
            width: 44,
            height: 44,
            decoration: BoxDecoration(
              gradient: gradient,
              borderRadius: BorderRadius.circular(12),
            ),
            child: Icon(icon, color: Colors.white, size: 22),
          ),
          const SizedBox(height: 16),
          Text(
            title,
            style: const TextStyle(
              fontSize: 15,
              fontWeight: FontWeight.w800,
              color: AppTheme.text,
              height: 1.25,
            ),
          ),
          const SizedBox(height: 6),
          Text(
            subtitle,
            style: const TextStyle(
              color: AppTheme.muted,
              fontSize: 11,
              height: 1.45,
            ),
          ),
          const SizedBox(height: 16),
          Row(
            children: [
              Text(
                'Open',
                style: TextStyle(
                  color: accentColor,
                  fontSize: 12,
                  fontWeight: FontWeight.w700,
                ),
              ),
              const SizedBox(width: 4),
              Icon(Icons.arrow_forward_rounded, size: 13, color: accentColor),
            ],
          ),
        ],
      ),
    ),
  );
}
