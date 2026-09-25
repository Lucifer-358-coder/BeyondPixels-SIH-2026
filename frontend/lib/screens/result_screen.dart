import 'package:flutter/material.dart';
import 'package:flutter/services.dart';
import '../theme/app_theme.dart';
import '../widgets/glass_card.dart';
import '../widgets/reviewer_panel.dart';
import '../widgets/evidence_summary.dart';

Map<String, dynamic> _section(dynamic value) =>
    value is Map<String, dynamic> ? value : <String, dynamic>{};

String _display(dynamic value) {
  if (value == null) return 'Not available';
  if (value is bool) return value ? 'Yes' : 'No';
  if (value is String) return value.replaceAll('_', ' ');
  return '$value';
}

class ResultScreen extends StatelessWidget {
  final bool isDocument;
  final String filename;
  final Uint8List imageBytes;
  final Map<String, dynamic> response;
  final String? backendUrl;
  final String? demoToken;
  const ResultScreen({super.key, required this.isDocument, required this.filename,
    required this.imageBytes, required this.response, this.backendUrl, this.demoToken});

  String get _summary {
    if (isDocument) {
      return response['screening_status'] == 'manual_review'
          ? 'Manual review required' : 'Inconclusive — review required';
    }
    final decision = _section(response['image_generation'])['decision'];
    if (decision == 'likely_ai_generated') return 'Potentially AI-generated';
    if (decision == 'likely_not_ai_generated') return 'No strong AI-generation indicators detected';
    return 'Inconclusive — review required';
  }

  @override
  Widget build(BuildContext context) {
    final ai = _section(response['image_generation']);
    final deepfake = _section(response['deepfake']);
    final ocr = _section(response['ocr']);
    final validation = _section(response['document_validation']);
    final consistency = _section(response['document_consistency']);
    final tampering = _section(response['single_image_review']);
    final artifacts = _section(response['visual_artifact_review']);
    final copyMove = _section(response['copy_move_review']);
    final portrait = _section(response['document_portrait_review']);
    final faceComparison = _section(response['face_verification']);
    final provenance = _section(response['provenance']);
    final c2pa = _section(response['content_credentials']);
    final standaloneTampering = _section(response['standalone_tampering_review']);
    final portraitReplacement = _section(response['portrait_replacement_review']);
    final referenceLocalization = _section(response['tampering_localization']);
    final authorizedSimilarity = _section(response['image_similarity']);
    final evidenceReport = _section(response['evidence_report']);
    final accent = isDocument ? AppTheme.primary : AppTheme.magenta;
    return Scaffold(
      appBar: AppBar(title: Text(isDocument ? 'Document Verification result' : 'Media result')),
      body: Center(child: ConstrainedBox(
        constraints: const BoxConstraints(maxWidth: 900),
        child: ListView(padding: const EdgeInsets.all(20), children: [
          Text('Screening report', style: Theme.of(context).textTheme.headlineLarge),
          const SizedBox(height: 8),
          Text(filename, style: const TextStyle(color: AppTheme.textSub)),
          const SizedBox(height: 16),
          GlassCard(borderColor: accent.withValues(alpha: .45), child: Column(
            crossAxisAlignment: CrossAxisAlignment.start, children: [
              Text(_summary, style: TextStyle(color: accent, fontSize: 22, fontWeight: FontWeight.w700)),
              const SizedBox(height: 10),
              const Text('Research screening only; not proof of identity, authenticity or fraud.',
                  style: TextStyle(color: AppTheme.textSub)),
            ],
          )),
          const SizedBox(height: 14),
          GlassCard(child: Column(children: [
            ClipRRect(borderRadius: BorderRadius.circular(12),
              child: InteractiveViewer(minScale: 1, maxScale: 4,
                child: Image.memory(imageBytes, height: 210, width: double.infinity,
                    fit: BoxFit.contain))),
            const SizedBox(height: 8),
            const Text('Original uploaded image · pinch or scroll to zoom',
                style: TextStyle(color: AppTheme.textSub, fontSize: 11)),
          ])),
          if (isDocument && evidenceReport.isNotEmpty) ...[
            const SizedBox(height: 14),
            EvidenceSummary(report: evidenceReport),
          ],
          if (isDocument) ...[
            const SizedBox(height: 14),
            _panel('OCR observations', AppTheme.primary, [
              _line('OCR', ocr['status']),
              _line('Spatial expiry crop', _section(ocr['expiry_extraction'])['status']),
              _line('Expiry method', _section(ocr['expiry_extraction'])['method']),
              ..._section(ocr['fields']).entries.map((e) => _line(_label(e.key), e.value)),
              ..._section(ocr['mrz_fields']).entries.map((e) => _line('MRZ ${_label(e.key)}', e.value)),
              const Text('OCR fields are unverified observations. No full document number is returned.',
                  style: TextStyle(color: AppTheme.textSub, fontSize: 11)),
            ]),
            const SizedBox(height: 14),
            _panel('Machine-readable zone consistency · TD1 / TD2 / TD3', AppTheme.primary, [
              _line('Status', validation['status']),
              _line('Document type', validation['document_type']),
              if (validation['mrz_format'] != null) _line('MRZ format', validation['mrz_format']),
              if (validation['expiry_date'] != null) _line('MRZ expiry date', validation['expiry_date']),
              ..._section(validation['checks']).entries.map((e) =>
                  _line(_label(e.key), e.value == true ? 'PASS' : e.value == false ? 'FAIL — review' : 'Not checked')),
              const Text('MRZ checks assess internal consistency, not document authenticity.',
                  style: TextStyle(color: AppTheme.textSub, fontSize: 11)),
            ]),
            const SizedBox(height: 14),
            _panel('Document portrait visibility · experimental', AppTheme.violet, [
              _line('Status', portrait['status']),
              _line('Observation', portrait['finding']),
              _line('Frontal-face candidates', portrait['faces_detected']),
              _line('Method', portrait['method']),
              if (_section(portrait['quality_observations']).isNotEmpty) ...[
                _line('Sharpness (measured, not scored)',
                    _section(portrait['quality_observations'])['sharpness_laplacian_variance']),
                _line('Mean brightness (0–255)',
                    _section(portrait['quality_observations'])['mean_brightness_0_255']),
                _line('Contrast standard deviation',
                    _section(portrait['quality_observations'])['contrast_std_0_255']),
              ],
              if (portrait['message'] is String)
                Text(portrait['message'] as String,
                    style: const TextStyle(color: AppTheme.textSub, fontSize: 11)),
              if (portrait['overlay_available'] == true &&
                  portrait['top_regions'] is List &&
                  (portrait['top_regions'] as List).isNotEmpty)
                _fieldLocationOverlay(imageBytes, portrait),
              const Text('Face visibility and uncalibrated quality measurements only. Optional photo comparison is reported separately; no portrait-replacement or identity verdict is produced. A missed face is not proof that a document has no portrait.',
                  style: TextStyle(color: AppTheme.textSub, fontSize: 11)),
            ]),
            const SizedBox(height: 14),
            _panel('Optional portrait-to-photo similarity · experimental', AppTheme.violet, [
              _line('Status', faceComparison['status']),
              _line('Observation', faceComparison['status'] == 'completed' ? 'Comparison completed — uncalibrated score' : faceComparison['finding']),
              _line('Document faces', faceComparison['document_face_count']),
              _line('Comparison-photo faces', faceComparison['photo_face_count']),
              _line('Model', faceComparison['method']),
              if (faceComparison['cosine_similarity'] is num)
                _line('Uncalibrated cosine similarity',
                    (faceComparison['cosine_similarity'] as num).toStringAsFixed(4)),
              if (faceComparison['message'] is String)
                Text(faceComparison['message'] as String,
                    style: const TextStyle(color: AppTheme.textSub, fontSize: 11)),
              const Text('Optional comparison only. No consented photo means not assessed. Similarity alone does not establish identity or prove portrait replacement.',
                  style: TextStyle(color: AppTheme.textSub, fontSize: 11)),
            ]),
            const SizedBox(height: 14),
            _panel('Standalone tampering evidence review · experimental', AppTheme.amber, [
              _line('Status', standaloneTampering['status']),
              _line('Finding', standaloneTampering['finding']),
              _line('Evidence signals', standaloneTampering['evidence_count']),
              if (standaloneTampering['evidence'] is List)
                ...(standaloneTampering['evidence'] as List).whereType<Map>().map((e) =>
                  _line('Signal', e['signal'])),
              if (standaloneTampering['message'] is String)
                Text(standaloneTampering['message'] as String,
                    style: const TextStyle(color: AppTheme.textSub, fontSize: 11)),
              const Text('This combines bounded single-image indicators for triage. It is not a validated standalone pixel-forgery classifier and never proves authenticity or forgery.',
                  style: TextStyle(color: AppTheme.textSub, fontSize: 11)),
            ]),
            const SizedBox(height: 14),
            _panel('Portrait replacement review · experimental', AppTheme.violet, [
              _line('Status', portraitReplacement['status']),
              _line('Finding', portraitReplacement['finding']),
              if (portraitReplacement['cosine_similarity'] is num)
                _line('Observed cosine similarity', (portraitReplacement['cosine_similarity'] as num).toStringAsFixed(4)),
              if (portraitReplacement['reference_threshold'] is num)
                _line('Reference threshold', (portraitReplacement['reference_threshold'] as num).toStringAsFixed(3)),
              if (portraitReplacement['message'] is String)
                Text(portraitReplacement['message'] as String,
                    style: const TextStyle(color: AppTheme.textSub, fontSize: 11)),
              const Text('Requires an authorized comparison photo. A mismatch candidate is not proof that a portrait was replaced; the threshold is not calibrated for this deployment.',
                  style: TextStyle(color: AppTheme.textSub, fontSize: 11)),
            ]),
            const SizedBox(height: 14),
            _panel('Document field-consistency review', AppTheme.amber, [
              _line('Status', consistency['status']),
              _line('Fields compared', consistency['fields_compared']),
              ..._section(consistency['comparisons']).entries.map((e) =>
                _line(_label(e.key), e.value)),
              _line('MRZ checksum issue', consistency['mrz_checksum_issue']),
              _line('Printed expiry conflict', consistency['printed_expiry_conflict']),
              if (consistency['message'] is String)
                Text(consistency['message'] as String,
                    style: const TextStyle(color: AppTheme.textSub, fontSize: 11)),
              const Text('Field comparisons are not visual tampering detection or proof of document authenticity.',
                  style: TextStyle(color: AppTheme.textSub, fontSize: 11)),
            ]),
            const SizedBox(height: 14),
            _panel('JPEG artifact diagnostic · unvalidated', AppTheme.amber, [
              _line('Status', artifacts['status']),
              _line('Finding', artifacts['finding']),
              _line('Method', artifacts['method']),
              _line('Relative residual regions', artifacts['diagnostic_regions']),
              if (artifacts['message'] is String)
                Text(artifacts['message'] as String,
                    style: const TextStyle(color: AppTheme.textSub, fontSize: 11)),
              const Text('JPEG only. Not a forgery detector; ordinary compression, text and graphics can create residuals. No tampering verdict or heatmap is produced.',
                  style: TextStyle(color: AppTheme.textSub, fontSize: 11)),
            ]),
            const SizedBox(height: 14),
            _panel('Repeated-texture diagnostic · experimental', AppTheme.amber, [
              _line('Status', copyMove['status']),
              _line('Finding', copyMove['finding']),
              _line('Candidate region pairs', copyMove['candidate_regions']),
              _line('Method', copyMove['method']),
              if (copyMove['message'] is String)
                Text(copyMove['message'] as String,
                    style: const TextStyle(color: AppTheme.textSub, fontSize: 11)),
              if (copyMove['overlay_available'] == true &&
                  copyMove['top_regions'] is List &&
                  (copyMove['top_regions'] as List).isNotEmpty)
                _fieldLocationOverlay(imageBytes, copyMove),
              const Text('This diagnostic finds some repeated image texture only. It cannot detect altered dates or portraits reliably, establish authenticity, or serve as a general forgery detector.',
                  style: TextStyle(color: AppTheme.textSub, fontSize: 11)),
            ]),
            const SizedBox(height: 14),
            _panel('Single-image field discrepancy location · experimental', AppTheme.amber, [
              _line('Status', tampering['status']),
              _line('Finding', tampering['finding']),
              _line('Method', tampering['method']),
              _line('Located disputed fields', tampering['regions_detected']),
              if (tampering['message'] is String)
                Text(tampering['message'] as String,
                    style: const TextStyle(color: AppTheme.textSub, fontSize: 11)),
              if (tampering['overlay_available'] == true &&
                  tampering['top_regions'] is List &&
                  (tampering['top_regions'] as List).isNotEmpty)
                _fieldLocationOverlay(imageBytes, tampering),
              const Text('A box locates a printed field disputed by independent OCR/MRZ checks. It does not identify pixel manipulation. No reference image needed; standalone forgery and portrait replacement remain unimplemented.',
                  style: TextStyle(color: AppTheme.textSub, fontSize: 11)),
            ]),
          ],
          if (!isDocument) ...[
          const SizedBox(height: 14),
          _panel('AI image analysis · experimental', AppTheme.magenta, [
            _line('Status', ai['status']),
            _line('Decision', ai['decision']),
            if (ai['ai_generation_score'] is num)
              _line('Whole-image model score', (ai['ai_generation_score'] as num).toStringAsFixed(4)),
            _line('Model', ai['model_version']),
            const Text('AI-image screening score only. This result does not establish image authenticity, document validity, identity, or fraud.',
                style: TextStyle(color: AppTheme.textSub, fontSize: 11)),
            if (_section(_section(ai['forensic_observations'])['signal_scores']).isNotEmpty)
              ExpansionTile(title: const Text('Measured model input signals'), children: [
                ..._section(_section(ai['forensic_observations'])['signal_scores']).entries.map((e) =>
                  _line(_label(e.key), e.value)),
                _line('Perspective inconclusive',
                    _section(ai['forensic_observations'])['perspective_inconclusive']),
                _line('Shadow inconclusive',
                    _section(ai['forensic_observations'])['shadow_inconclusive']),
              ]),
          ]),
          ],
          if (!isDocument) ...[
            const SizedBox(height: 14),
            _panel('Face-based deepfake analysis · experimental', AppTheme.violet, [
              _line('Status', deepfake['status']),
              _line('Face-manipulation finding', deepfake['decision']),
              _line('Faces detected', deepfake['face_count']),
              _line('Faces analyzed', deepfake['faces_analyzed']),
              _line('Research model', deepfake['model']),
              if (deepfake['message'] is String)
                Text(deepfake['message'] as String,
                    style: const TextStyle(color: AppTheme.textSub, fontSize: 11)),
              if (deepfake['faces'] is List && (deepfake['faces'] as List).isNotEmpty)
                ExpansionTile(
                  title: const Text('Individual face observations'),
                  children: [
                    ...(deepfake['faces'] as List).asMap().entries.map((entry) =>
                      _line('Face ${entry.key + 1}',
                        '${_display(_section(entry.value)['decision'])} · raw model score: ${_display(_section(entry.value)['fake_score'])}')),
                  ],
                ),
              const Text('No face means not assessed. These scores are not calibrated probabilities or identity verification.',
                  style: TextStyle(color: AppTheme.textSub, fontSize: 11)),
            ]),
          ],
          if (isDocument) ...[
            const SizedBox(height: 14),
            _panel('File metadata provenance · diagnostic', AppTheme.amber, [
              _line('Status', provenance['status']),
              _line('Finding', provenance['finding']),
              _line('Format', provenance['format']),
              _line('Embedded metadata', provenance['metadata_present']),
              _line('Software tag', provenance['software']),
              _line('Camera make', provenance['camera_make']),
              _line('Camera model', provenance['camera_model']),
              _line('Metadata date/time', provenance['datetime']),
              _line('C2PA/JUMBF marker candidate', provenance['c2pa_marker_candidate']),
              if (provenance['message'] is String)
                Text(provenance['message'] as String,
                    style: const TextStyle(color: AppTheme.textSub, fontSize: 11)),
              const Text('Metadata is editable and removable. This diagnostic does not validate cryptographic provenance, document authenticity, or tampering.',
                  style: TextStyle(color: AppTheme.textSub, fontSize: 11)),
            ]),
            const SizedBox(height: 14),
            _panel('Content Credentials (C2PA) · offline verification', AppTheme.amber, [
              _line('Status', c2pa['status']),
              _line('Finding', c2pa['finding']),
              _line('Embedded manifest', c2pa['manifest_present']),
              _line('SDK validation state', c2pa['validation_state']),
              _line('Signer trust', c2pa['signer_trust']),
              if (c2pa['validation_issues'] != null)
                _line('Reported validation issues', c2pa['validation_issues']),
              if (c2pa['message'] is String)
                Text(c2pa['message'] as String,
                    style: const TextStyle(color: AppTheme.textSub, fontSize: 11)),
              const Text('An absent, untrusted or unverifiable manifest is not a forgery finding. C2PA does not verify a government-issued ID or a person’s identity.',
                  style: TextStyle(color: AppTheme.textSub, fontSize: 11)),
            ]),
          ],
          if (isDocument) ...[
            const SizedBox(height: 14),
            _panel('Optional trusted PNG pixel differences · experimental', AppTheme.amber, [
              _line('Status', referenceLocalization['status']),
              _line('Finding', referenceLocalization['finding']),
              _line('Located regions', referenceLocalization['regions_detected']),
              if (referenceLocalization['message'] is String)
                Text(referenceLocalization['message'] as String,
                  style: const TextStyle(color: AppTheme.textSub, fontSize: 11)),
              if (referenceLocalization['overlay_available'] == true &&
                  referenceLocalization['top_regions'] is List &&
                  (referenceLocalization['top_regions'] as List).isNotEmpty)
                _fieldLocationOverlay(imageBytes, referenceLocalization),
              const Text('Only aligned, authorized PNG pairs. Changed pixels alone are not evidence of forgery.',
                style: TextStyle(color: AppTheme.textSub, fontSize: 11)),
            ]),
            const SizedBox(height: 14),
            _panel('Authorized in-session duplicate candidates · experimental', AppTheme.amber, [
              _line('Status', authorizedSimilarity['status']),
              _line('Finding', authorizedSimilarity['finding']),
              _line('References compared', authorizedSimilarity['references_compared']),
              if (authorizedSimilarity['candidates'] is List)
                ...(authorizedSimilarity['candidates'] as List).whereType<Map>().map((e) =>
                  _line('Reference ${e['reference_index']}', e['observation'])),
              if (authorizedSimilarity['message'] is String)
                Text(authorizedSimilarity['message'] as String,
                  style: const TextStyle(color: AppTheme.textSub, fontSize: 11)),
            ]),
          ],
          if (isDocument && response['review_ref'] is String &&
              backendUrl != null && demoToken != null) ...[
            const SizedBox(height: 14),
            ReviewerPanel(reviewRef: response['review_ref'] as String,
              backendUrl: backendUrl!, demoToken: demoToken!),
          ],
          if (isDocument) ...[
            const SizedBox(height: 14),
            _panel('Additional checks', AppTheme.amber, [
              _line('Standalone pixel-forgery classifier', 'not implemented'),
              _line('Multi-signal tampering review', standaloneTampering['status']),
              _line('Identity verification', 'not established'),
              _line('Portrait replacement review', portraitReplacement['status']),
              _line('Authorized reference similarity', authorizedSimilarity['status']),
              _line('Provenance', _section(response['provenance'])['status']),
            ]),
          ],
          if (response['review_notes'] is List) ...[
            const SizedBox(height: 14),
            _panel('Review notes', AppTheme.amber, [
              ...(response['review_notes'] as List).map((note) => Padding(
                padding: const EdgeInsets.only(bottom: 7),
                child: Text('• ${_display(note)}', style: const TextStyle(color: AppTheme.textSub)),
              )),
            ]),
          ],
          const SizedBox(height: 18),
          FilledButton.icon(
            onPressed: () async {
              final report = _summaryText();
              await Clipboard.setData(ClipboardData(text: report));
              if (context.mounted) {
                ScaffoldMessenger.of(context).showSnackBar(
                  const SnackBar(content: Text('Text-only screening summary copied.')),
                );
              }
            },
            icon: const Icon(Icons.copy_all_outlined), label: const Text('Copy text summary'),
          ),
          const SizedBox(height: 12),
          OutlinedButton.icon(onPressed: () => Navigator.popUntil(context, (route) => route.isFirst),
              icon: const Icon(Icons.home_outlined), label: const Text('Home')),
        ]),
      )),
    );
  }

  static Widget _fieldLocationOverlay(Uint8List original, Map<String, dynamic> result) {
    final width = (result['image_width'] as num?)?.toDouble() ?? 0;
    final height = (result['image_height'] as num?)?.toDouble() ?? 0;
    final regions = result['top_regions'];
    if (width <= 0 || height <= 0 || regions is! List) return const SizedBox.shrink();
    return Padding(
      padding: const EdgeInsets.only(top: 12, bottom: 12),
      child: LayoutBuilder(builder: (context, constraints) {
        final displayWidth = constraints.maxWidth;
        final displayHeight = displayWidth * height / width;
        return SizedBox(width: displayWidth, height: displayHeight,
          child: Stack(children: [
            Positioned.fill(child: Image.memory(original, fit: BoxFit.fill)),
            ...regions.whereType<Map>().map((raw) {
              final box = Map<String, dynamic>.from(raw);
              final x = ((box['x'] as num?)?.toDouble() ?? 0).clamp(0.0, 1.0).toDouble();
              final y = ((box['y'] as num?)?.toDouble() ?? 0).clamp(0.0, 1.0).toDouble();
              final w = ((box['width'] as num?)?.toDouble() ?? 0).clamp(0.0, 1.0 - x).toDouble();
              final h = ((box['height'] as num?)?.toDouble() ?? 0).clamp(0.0, 1.0 - y).toDouble();
              return Positioned(left: x * displayWidth, top: y * displayHeight,
                width: w * displayWidth, height: h * displayHeight,
                child: IgnorePointer(child: DecoratedBox(decoration: BoxDecoration(
                  border: Border.all(color: AppTheme.amber, width: 2),
                  color: AppTheme.amber.withValues(alpha: .13),
                ))));
            }),
          ]),
        );
      }),
    );
  }

  static String _label(String key) => key.replaceAll('_', ' ');
  static Widget _line(String name, dynamic value) => Padding(
    padding: const EdgeInsets.only(bottom: 9),
    child: Row(crossAxisAlignment: CrossAxisAlignment.start, children: [
      Expanded(flex: 2, child: Text(name, style: const TextStyle(color: AppTheme.textSub, fontSize: 12))),
      Expanded(flex: 3, child: SelectableText(_display(value),
        style: const TextStyle(color: AppTheme.text, fontSize: 12))),
    ]),
  );
  static Widget _panel(String title, Color color, List<Widget> children) => GlassCard(
    borderColor: color.withValues(alpha: .28),
    child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
      Text(title, style: TextStyle(color: color, fontWeight: FontWeight.w700, fontSize: 16)),
      const SizedBox(height: 14),
      ...children,
    ]),
  );

  String _summaryText() {
    final ai = _section(response['image_generation']);
    final ocr = _section(response['ocr']);
    final mrz = _section(response['document_validation']);
    final consistency = _section(response['document_consistency']);
    return [
      'BeyondPixels — research screening summary',
      'File: $filename',
      'Outcome: $_summary',
      if (isDocument) 'OCR: ${_display(ocr['status'])}',
      if (isDocument) 'Expiry extraction: ${_display(_section(ocr['expiry_extraction'])['status'])}',
      if (isDocument) 'MRZ consistency: ${_display(mrz['status'])}',
      if (isDocument) 'Field consistency: ${_display(consistency['status'])}',
      if (isDocument) 'Comparable fields: ${_display(consistency['fields_compared'])}',
      if (isDocument) 'Single-image disputed field location: ${_display(_section(response['single_image_review'])['finding'])}',
      if (isDocument) 'Document portrait visibility: ${_display(_section(response['document_portrait_review'])['status'])}',
      if (isDocument) 'Portrait replacement detection: not implemented',
      if (isDocument) 'Repeated-texture diagnostic: ${_display(_section(response['copy_move_review'])['finding'])}',
      if (isDocument) 'Metadata provenance diagnostic: ${_display(_section(response['provenance'])['finding'])}',
      if (isDocument) 'Standalone tampering detection: not implemented',
      if (isDocument) 'Paired PNG localization: ${_display(_section(response['tampering_localization'])['finding'])}',
      if (isDocument) 'Authorized reference similarity: ${_display(_section(response['image_similarity'])['finding'])}',
      if (isDocument) 'Research evidence overview: ${_display(_section(response['evidence_report'])['status'])}',
      if (isDocument) 'Local demo review audit is optional; no audit action in this copied summary.',
      if (!isDocument) 'AI image analysis: ${_display(ai['decision'])}',
      if (!isDocument) 'Model: ${_display(ai['model_version'])}',
      if (!isDocument) 'Deepfake status: ${_display(_section(response['deepfake'])['status'])}',
      if (!isDocument) 'Deepfake finding: ${_display(_section(response['deepfake'])['decision'])}',
      'Screening aid only; does not establish identity, authenticity or fraud.',
    ].join('\n');
  }
}
