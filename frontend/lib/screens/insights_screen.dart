import 'package:flutter/material.dart';
import '../models/session_history.dart';
import '../theme/app_theme.dart';
import '../widgets/glass_card.dart';

class InsightsScreen extends StatelessWidget {
  const InsightsScreen({super.key});
  @override
  Widget build(BuildContext context) => Scaffold(
    appBar: AppBar(title: const Text('Insights')),
    body: AnimatedBuilder(animation: SessionHistory.instance, builder: (context, _) {
      final items = SessionHistory.instance.items;
      final docs = items.where((e) => e.isDocument).length;
      final manual = items.where((e) => e.status == 'manual_review').length;
      return Center(child: ConstrainedBox(constraints: const BoxConstraints(maxWidth: 850),
        child: ListView(padding: const EdgeInsets.all(20), children: [
          const Text('Session activity', style: TextStyle(color: AppTheme.text,
              fontWeight: FontWeight.w700, fontSize: 21)),
          const SizedBox(height: 8),
          const Text('Based only on completed requests in this app session. No accuracy claims.',
              style: TextStyle(color: AppTheme.textSub)),
          const SizedBox(height: 18),
          _stat('Total analyses', '${items.length}', AppTheme.primary),
          const SizedBox(height: 10),
          _stat('Documents screened', '$docs', AppTheme.primary),
          const SizedBox(height: 10),
          _stat('Media analyzed', '${items.length - docs}', AppTheme.magenta),
          const SizedBox(height: 10),
          _stat('Document manual-review results', '$manual', AppTheme.amber),
          const SizedBox(height: 18),
          if (items.isEmpty) const GlassCard(child: Text(
              'No analyses recorded yet. The dashboard populates after a successful backend response.',
              style: TextStyle(color: AppTheme.textSub))),
        ]),
      ));
    }),
  );

  static Widget _stat(String label, String value, Color accent) => GlassCard(
    borderColor: accent.withValues(alpha: .25),
    child: Row(children: [
      Expanded(child: Text(label, style: const TextStyle(color: AppTheme.textSub))),
      Text(value, style: TextStyle(color: accent, fontSize: 24, fontWeight: FontWeight.w700)),
    ]),
  );
}
