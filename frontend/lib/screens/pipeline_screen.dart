import 'dart:typed_data';
import 'package:flutter/material.dart';
import '../models/session_history.dart';
import '../services/screening_api.dart';
import '../theme/app_theme.dart';
import '../widgets/glass_card.dart';
import 'result_screen.dart';

class PipelineScreen extends StatefulWidget {
  final bool isDocument;
  final String filename;
  final Uint8List imageBytes;
  final Uint8List? comparisonPhoto;
  final Uint8List? referenceBytes;
  final List<Uint8List> authorizedReferences;
  final String? comparisonFilename;
  final String backendUrl;
  final String demoToken;
  const PipelineScreen({super.key, required this.isDocument, required this.filename,
    required this.imageBytes, required this.backendUrl, required this.demoToken,
    this.comparisonPhoto, this.comparisonFilename, this.referenceBytes,
    this.authorizedReferences = const []});

  @override
  State<PipelineScreen> createState() => _PipelineScreenState();
}

class _PipelineScreenState extends State<PipelineScreen> {
  bool _loading = true;
  String? _error;
  Map<String, dynamic>? _result;

  @override
  void initState() {
    super.initState();
    _execute();
  }

  Future<void> _execute() async {
    setState(() { _loading = true; _error = null; _result = null; });
    try {
      final response = await ScreeningApi.analyze(
        document: widget.isDocument, backendUrl: widget.backendUrl,
        demoToken: widget.demoToken, imageBytes: widget.imageBytes,
        filename: widget.filename, comparisonPhoto: widget.comparisonPhoto,
        comparisonFilename: widget.comparisonFilename,
        referenceBytes: widget.referenceBytes,
        authorizedReferences: widget.authorizedReferences,
      );
      if (!mounted) return;
      SessionHistory.instance.add(SessionEntry(
        widget.filename, widget.isDocument,
        widget.isDocument ? '${response['screening_status'] ?? 'inconclusive'}'
            : '${(response['image_generation'] as Map)['decision'] ?? 'inconclusive'}',
        DateTime.now(),
      ));
      setState(() { _result = response; _loading = false; });
    } catch (error) {
      if (mounted) {
        setState(() {
        _loading = false;
        _error = error is ScreeningException ? error.message : 'Analysis failed. Try again.';
        });
      }
    }
  }

  String _statusFor(String key) {
    if (_result == null) return _loading ? 'pending' : 'not_checked';
    final result = _result!;
    if (key == 'image') return '${(result['image_generation'] as Map?)?['status'] ?? 'unavailable'}';
    if (key == 'deepfake') return '${(result['deepfake'] as Map?)?['status'] ?? 'unavailable'}';
    if (key == 'report') return '${(result['evidence_report'] as Map?)?['status'] ?? 'not_assessed'}';
    if (key == 'reference') return '${(result['tampering_localization'] as Map?)?['status'] ?? 'not_assessed'}';
    if (key == 'similarity') return '${(result['image_similarity'] as Map?)?['status'] ?? 'not_assessed'}';
    if (key == 'ocr') return '${(result['ocr'] as Map?)?['status'] ?? 'unavailable'}';
    if (key == 'mrz') return '${(result['document_validation'] as Map?)?['status'] ?? 'not_checked'}';
    if (key == 'face') return '${(result['face_verification'] as Map?)?['status'] ?? 'not_implemented'}';
    if (key == 'tamper') return '${(result['standalone_tampering_review'] as Map?)?['status'] ?? 'not_assessed'}';
    if (key == 'portraitReplace') return '${(result['portrait_replacement_review'] as Map?)?['status'] ?? 'not_assessed'}';
    return 'not_checked';
  }

  Color _colorFor(String state) {
    if (state == 'completed' || state == 'checks_passed') return AppTheme.success;
    if (state == 'checksum_mismatch' || state == 'expired' || state == 'invalid_format') return AppTheme.amber;
    if (state == 'pending') return AppTheme.primary;
    return AppTheme.textSub;
  }

  @override
  Widget build(BuildContext context) {
    final accent = widget.isDocument ? AppTheme.primary : AppTheme.magenta;
    final stages = widget.isDocument
        ? [('OCR extraction', 'ocr'), ('TD1 / TD2 / TD3 MRZ checks', 'mrz'),
           ('Standalone tampering evidence review', 'tamper'),
           ('Optional face comparison', 'face'),
           ('Portrait replacement review', 'portraitReplace'),
           ('Optional reference pixel differences', 'reference'),
           ('Optional authorized image similarity', 'similarity'),
           ('Evidence overview', 'report')]
        : [('Whole-image generation analysis', 'image'),
           ('Face-based deepfake analysis', 'deepfake'), ('Evidence report', 'report')];
    return Scaffold(
      appBar: AppBar(title: const Text('Analysis pipeline')),
      body: Center(child: ConstrainedBox(
        constraints: const BoxConstraints(maxWidth: 800),
        child: ListView(padding: const EdgeInsets.all(20), children: [
          Text(widget.isDocument ? 'Document Verification' : 'Media analysis',
              style: Theme.of(context).textTheme.headlineLarge),
          const SizedBox(height: 8),
          Text(widget.filename, style: const TextStyle(color: AppTheme.textSub)),
          const SizedBox(height: 20),
          if (_loading) ...[
            LinearProgressIndicator(color: accent),
            const SizedBox(height: 12),
            const Text('Waiting for the backend. Individual stage completion is not streamed.',
                style: TextStyle(color: AppTheme.textSub)),
          ],
          const SizedBox(height: 12),
          ...stages.map((s) {
            final state = _statusFor(s.$2);
            return Padding(padding: const EdgeInsets.only(bottom: 10), child: GlassCard(
              padding: const EdgeInsets.all(16),
              child: Row(children: [
                Icon(state == 'completed' || state == 'checks_passed'
                    ? Icons.check_circle_outline : Icons.info_outline,
                    color: _colorFor(state)),
                const SizedBox(width: 12),
                Expanded(child: Text(s.$1, style: const TextStyle(color: AppTheme.text))),
                Text(state.replaceAll('_', ' '), style: TextStyle(color: _colorFor(state), fontSize: 11)),
              ]),
            ));
          }),
          if (_error != null) ...[
            const SizedBox(height: 14),
            Text(_error!, style: const TextStyle(color: AppTheme.danger)),
            const SizedBox(height: 12),
            if (_error!.contains('Unauthorized')) ...[
              FilledButton.icon(
                onPressed: () => Navigator.pop(context),
                icon: const Icon(Icons.key_outlined),
                label: const Text('Back to token settings'),
              ),
            ] else ...[
              FilledButton.icon(onPressed: _execute, icon: const Icon(Icons.refresh),
                  label: const Text('Retry analysis')),
            ],
          ],
          if (_result != null) ...[
            const SizedBox(height: 12),
            FilledButton.icon(onPressed: () => Navigator.pushReplacement(context,
              MaterialPageRoute<void>(builder: (_) => ResultScreen(
                isDocument: widget.isDocument, filename: widget.filename,
                imageBytes: widget.imageBytes, response: _result!,
                backendUrl: widget.backendUrl, demoToken: widget.demoToken,
              )),
            ), icon: const Icon(Icons.description_outlined), label: const Text('View actual results'),
              style: FilledButton.styleFrom(backgroundColor: accent, foregroundColor: AppTheme.background)),
          ],
        ]),
      )),
    );
  }
}
