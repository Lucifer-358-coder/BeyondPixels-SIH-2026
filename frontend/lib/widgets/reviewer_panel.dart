import 'package:flutter/material.dart';
import '../services/screening_api.dart';
import '../theme/app_theme.dart';
import 'glass_card.dart';

/// Explicit, local-demo-only, action-code audit. Not production RBAC or tamper-proof.
class ReviewerPanel extends StatefulWidget {
  final String reviewRef;
  final String backendUrl;
  final String demoToken;
  const ReviewerPanel({super.key, required this.reviewRef,
    required this.backendUrl, required this.demoToken});

  @override
  State<ReviewerPanel> createState() => _ReviewerPanelState();
}

class _ReviewerPanelState extends State<ReviewerPanel> {
  String? _selected;
  String? _recorded;
  String? _error;
  bool _busy = false;

  Future<void> _submit() async {
    if (_busy || _selected == null) return;
    setState(() { _busy = true; _error = null; });
    try {
      final event = await ScreeningApi.submitReview(
        backendUrl: widget.backendUrl, demoToken: widget.demoToken,
        reviewRef: widget.reviewRef, action: _selected!,
      );
      if (mounted) {
        setState(() {
          _recorded = '${event['action']} · ${event['recorded_at']}';
          _selected = null;
        });
      }
    } on ScreeningException catch (e) {
      if (mounted) setState(() => _error = e.message);
    } catch (_) {
      if (mounted) setState(() => _error = 'Could not record the review action.');
    } finally {
      if (mounted) setState(() => _busy = false);
    }
  }

  @override
  Widget build(BuildContext context) => GlassCard(child: Column(
    crossAxisAlignment: CrossAxisAlignment.start,
    children: [
      const Text('Local review audit · demo only',
        style: TextStyle(color: AppTheme.primary, fontWeight: FontWeight.w700)),
      const SizedBox(height: 8),
      const Text('Choose an operator action. Only an action code, random review reference and UTC time are saved locally; no image, OCR fields or comparison photo. This is not role-based access control or a tamper-proof audit.',
        style: TextStyle(color: AppTheme.textSub, fontSize: 12)),
      const SizedBox(height: 8),
      DropdownButtonFormField<String>(
        key: ValueKey(_recorded),
        initialValue: _selected,
        items: const [
          DropdownMenuItem(value: 'reviewed', child: Text('Reviewed — no decision recorded')),
          DropdownMenuItem(value: 'follow_up_required', child: Text('Follow-up required')),
          DropdownMenuItem(value: 'inconclusive', child: Text('Inconclusive')),
        ],
        onChanged: _busy ? null : (v) => setState(() => _selected = v),
        decoration: const InputDecoration(labelText: 'Review action'),
      ),
      const SizedBox(height: 10),
      FilledButton.icon(
        onPressed: _busy || _selected == null ? null : _submit,
        icon: const Icon(Icons.fact_check_outlined),
        label: Text(_busy ? 'Saving…' : 'Record local review action'),
      ),
      if (_recorded != null) Padding(padding: const EdgeInsets.only(top: 8),
        child: Text('Recorded: $_recorded',
          style: const TextStyle(color: AppTheme.success, fontSize: 12))),
      if (_error != null) Padding(padding: const EdgeInsets.only(top: 8),
        child: Text(_error!, style: const TextStyle(color: AppTheme.danger))),
    ],
  ));
}
