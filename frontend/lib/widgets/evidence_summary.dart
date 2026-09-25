import 'package:flutter/material.dart';
import '../theme/app_theme.dart';
import 'glass_card.dart';

/// Explainability means exposing actual checks, not inventing confidence or verdicts.
class EvidenceSummary extends StatelessWidget {
  final Map<String, dynamic> report;
  const EvidenceSummary({super.key, required this.report});

  @override
  Widget build(BuildContext context) {
    final items = report['observations'];
    return GlassCard(child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
      const Text('Evidence overview · research only',
        style: TextStyle(color: AppTheme.primary, fontWeight: FontWeight.w700, fontSize: 16)),
      const SizedBox(height: 8),
      const Text('Status and finding codes, not an authenticity or identity score.',
        style: TextStyle(color: AppTheme.textSub, fontSize: 12)),
      if (items is List) ...items.whereType<Map>().map((entry) => Padding(
        padding: const EdgeInsets.symmetric(vertical: 7),
        child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
          Text('${entry['check'] ?? 'Check'}',
            style: const TextStyle(color: AppTheme.text, fontWeight: FontWeight.w600)),
          Text('${entry['status'] ?? 'not assessed'} · ${entry['finding'] ?? 'not assessed'}'
            .replaceAll('_', ' '),
            style: const TextStyle(color: AppTheme.textSub, fontSize: 12)),
        ]),
      )),
      const SizedBox(height: 8),
      const Text('Inconclusive or unavailable evidence is never treated as a pass.',
        style: TextStyle(color: AppTheme.amber, fontSize: 12)),
    ]));
  }
}
