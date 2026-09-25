import 'package:flutter/material.dart';
import 'package:flutter/services.dart';

import 'screens/home_screen.dart';
import 'screens/history_screen.dart';
import 'screens/insights_screen.dart';
import 'screens/profile_screen.dart';
import 'theme/app_theme.dart';

void main() {
  WidgetsFlutterBinding.ensureInitialized();
  SystemChrome.setSystemUIOverlayStyle(const SystemUiOverlayStyle(
    statusBarColor: Colors.transparent,
    statusBarIconBrightness: Brightness.light,
    systemNavigationBarColor: AppTheme.surface,
    systemNavigationBarIconBrightness: Brightness.light,
  ));
  runApp(const BeyondPixelsApp());
}

class BeyondPixelsApp extends StatelessWidget {
  const BeyondPixelsApp({super.key});

  @override
  Widget build(BuildContext context) => MaterialApp(
    debugShowCheckedModeBanner: false,
    title: 'BeyondPixels',
    theme: AppTheme.dark(),
    home: const AppShell(),
  );
}

// ── App shell with animated bottom nav ────────────────────────────────────────

class AppShell extends StatefulWidget {
  const AppShell({super.key});

  @override
  State<AppShell> createState() => _AppShellState();
}

class _AppShellState extends State<AppShell> with TickerProviderStateMixin {
  int _currentIndex = 0;

  // Keep all screens alive while switching tabs
  static const _screens = [
    HomeScreen(),
    HistoryScreen(),
    InsightsScreen(),
    ProfileScreen(),
  ];

  static const _destinations = [
    NavigationDestination(
      icon: Icon(Icons.home_outlined),
      selectedIcon: Icon(Icons.home_rounded),
      label: 'Home',
    ),
    NavigationDestination(
      icon: Icon(Icons.history_outlined),
      selectedIcon: Icon(Icons.history_rounded),
      label: 'History',
    ),
    NavigationDestination(
      icon: Icon(Icons.insights_outlined),
      selectedIcon: Icon(Icons.insights_rounded),
      label: 'Insights',
    ),
    NavigationDestination(
      icon: Icon(Icons.person_outline_rounded),
      selectedIcon: Icon(Icons.person_rounded),
      label: 'About',
    ),
  ];

  void _onTabChanged(int index) {
    if (index == _currentIndex) return;
    HapticFeedback.selectionClick();
    setState(() => _currentIndex = index);
  }

  @override
  Widget build(BuildContext context) {
    return LayoutBuilder(builder: (context, constraints) {
      final desktop = constraints.maxWidth >= 920;
      return Scaffold(
        body: Row(children: [
          if (desktop) NavigationRail(
            backgroundColor: AppTheme.surface,
            selectedIndex: _currentIndex,
            labelType: NavigationRailLabelType.all,
            onDestinationSelected: _onTabChanged,
            destinations: const [
              NavigationRailDestination(icon: Icon(Icons.home_outlined), label: Text('Home')),
              NavigationRailDestination(icon: Icon(Icons.history_outlined), label: Text('History')),
              NavigationRailDestination(icon: Icon(Icons.insights_outlined), label: Text('Insights')),
              NavigationRailDestination(icon: Icon(Icons.info_outline_rounded), label: Text('About')),
            ],
          ),
          Expanded(child: IndexedStack(index: _currentIndex, children: _screens)),
        ]),
        bottomNavigationBar: desktop ? null : _AnimatedNavBar(
          currentIndex: _currentIndex,
          onDestinationSelected: _onTabChanged,
          destinations: _destinations,
        ),
      );
    });
  }
}

// ── Custom nav bar with slide-in indicator ─────────────────────────────────────

class _AnimatedNavBar extends StatefulWidget {
  final int currentIndex;
  final ValueChanged<int> onDestinationSelected;
  final List<NavigationDestination> destinations;

  const _AnimatedNavBar({
    required this.currentIndex,
    required this.onDestinationSelected,
    required this.destinations,
  });

  @override
  State<_AnimatedNavBar> createState() => _AnimatedNavBarState();
}

class _AnimatedNavBarState extends State<_AnimatedNavBar> {
  @override
  Widget build(BuildContext context) {
    return Container(
      decoration: const BoxDecoration(
        color: AppTheme.surface,
        border: Border(top: BorderSide(color: AppTheme.border)),
      ),
      child: NavigationBar(
        selectedIndex: widget.currentIndex,
        onDestinationSelected: widget.onDestinationSelected,
        destinations: widget.destinations,
        animationDuration: const Duration(milliseconds: 300),
        backgroundColor: AppTheme.surface,
        elevation: 0,
        surfaceTintColor: Colors.transparent,
        shadowColor: Colors.transparent,
      ),
    );
  }
}
