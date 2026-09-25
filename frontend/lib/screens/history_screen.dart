import 'package:flutter/material.dart';
import '../models/session_history.dart';
import '../theme/app_theme.dart';
import '../widgets/glass_card.dart';

class HistoryScreen extends StatelessWidget {
  const HistoryScreen({super.key});
  @override
  Widget build(BuildContext context) => Scaffold(
    appBar: AppBar(title: const Text('History')),
    body: AnimatedBuilder(animation: SessionHistory.instance, builder: (context, _) {
      final entries = SessionHistory.instance.items;
      return Center(child: ConstrainedBox(constraints: const BoxConstraints(maxWidth: 850),
        child: entries.isEmpty
          ? const Center(child: Padding(padding: EdgeInsets.all(24), child: Text(
              'No analyses in this session yet. History is temporary and is cleared when the app closes.',
              textAlign: TextAlign.center, style: TextStyle(color: AppTheme.textSub))))
          : ListView(padding: const EdgeInsets.all(20), children: [
              const Text('This session only · no document images or identity data saved',
                  style: TextStyle(color: AppTheme.textSub, fontSize: 12)),
              const SizedBox(height: 12),
              ...entries.map((entry) => Padding(padding: const EdgeInsets.only(bottom: 10),
                  child: GlassCard(child: Row(children: [
                    Icon(entry.isDocument ? Icons.badge_outlined : Icons.image_outlined,
                        color: entry.isDocument ? AppTheme.primary : AppTheme.magenta),
                    const SizedBox(width: 12),
                    Expanded(child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
                      Text(entry.filename, style: const TextStyle(color: AppTheme.text, fontWeight: FontWeight.w600)),
                      Text('${entry.isDocument ? 'Document' : 'Media'} · ${entry.time.toLocal()}',
                          style: const TextStyle(color: AppTheme.textSub, fontSize: 11)),
                    ])),
                    Text(entry.status.replaceAll('_', ' '),
                        style: const TextStyle(color: AppTheme.amber, fontSize: 11)),
                  ])))),
              OutlinedButton.icon(onPressed: SessionHistory.instance.clear,
                  icon: const Icon(Icons.delete_outline), label: const Text('Clear session history')),
            ]),
      ));
    }),
  );
}
