import 'dart:typed_data';
import 'dart:ui' as ui;
import 'package:file_picker/file_picker.dart';
import 'package:flutter/material.dart';
import '../theme/app_theme.dart';
import '../widgets/glass_card.dart';
import 'pipeline_screen.dart';
import '../services/local_demo_session.dart';

class AnalyzeScreen extends StatefulWidget {
  final String kind;
  const AnalyzeScreen({super.key, required this.kind});
  @override
  State<AnalyzeScreen> createState() => _AnalyzeScreenState();
}

class _AnalyzeScreenState extends State<AnalyzeScreen> {
  Uint8List? _bytes;
  Uint8List? _comparisonPhoto;
  Uint8List? _referenceBytes;
  String? _referenceName;
  List<Uint8List> _authorizedReferences = [];
  List<String> _authorizedNames = [];
  String? _comparisonName;
  String? _filename;
  int? _width;
  int? _height;
  String? _error;
  final _backend = TextEditingController(text: LocalDemoSession.backendUrl);
  final _token = TextEditingController(text: LocalDemoSession.demoToken);

  bool get _isDocument => widget.kind == 'document';

  @override
  void dispose() {
    _backend.dispose();
    _token.dispose();
    super.dispose();
  }

  Future<void> _pickFile() async {
    try {
      final selection = await FilePicker.platform.pickFiles(
        type: FileType.custom,
        allowedExtensions: ['jpg', 'jpeg', 'png'],
        withData: true,
      );
      if (selection == null || !mounted) return;
      final file = selection.files.single;
      final bytes = file.bytes;
      if (bytes == null || bytes.isEmpty || bytes.length > 8 * 1024 * 1024) {
        setState(() => _error = 'Select a JPG or PNG smaller than 8 MB.');
        return;
      }
      final ext = file.name.toLowerCase().split('.').last;
      if (!['jpg', 'jpeg', 'png'].contains(ext)) {
        setState(() => _error = 'Only JPG and PNG images are supported.');
        return;
      }
      final codec = await ui.instantiateImageCodec(bytes);
      final frame = await codec.getNextFrame();
      final width = frame.image.width;
      final height = frame.image.height;
      frame.image.dispose();
      codec.dispose();
      if (width * height > 16000000 || !mounted) {
        if (mounted) setState(() => _error = 'Image exceeds the 16-megapixel limit.');
        return;
      }
      setState(() {
        _bytes = bytes;
        _filename = file.name;
        _width = width;
        _height = height;
        _error = null;
      });
    } catch (_) {
      if (mounted) setState(() => _error = 'Could not open this image. Select another JPG or PNG.');
    }
  }

  Future<void> _pickComparisonPhoto() async {
    try {
      final selection = await FilePicker.platform.pickFiles(
        type: FileType.custom, allowedExtensions: ['jpg', 'jpeg', 'png'],
        withData: true,
      );
      if (selection == null || !mounted) return;
      final file = selection.files.single;
      final data = file.bytes;
      if (data == null || data.isEmpty || data.length > 8 * 1024 * 1024) {
        setState(() => _error = 'Select a comparison photo smaller than 8 MB.');
        return;
      }
      final ext = file.name.toLowerCase().split('.').last;
      if (!['jpg', 'jpeg', 'png'].contains(ext)) {
        setState(() => _error = 'Use a JPG or PNG comparison photo.');
        return;
      }
      final codec = await ui.instantiateImageCodec(data);
      final frame = await codec.getNextFrame();
      final w = frame.image.width, h = frame.image.height;
      frame.image.dispose();
      codec.dispose();
      if (w * h > 16000000 || !mounted) {
        if (mounted) {
          setState(() => _error = 'Comparison photo exceeds 16 MP.');
        }
        return;
      }
      setState(() {
        _comparisonPhoto = data;
        _comparisonName = file.name;
        _error = null;
      });
    } catch (_) {
      if (mounted) {
        setState(() => _error = 'Could not open comparison photo.');
      }
    }
  }

  Future<void> _pickTrustedReference() async {
    try {
      final picked = await FilePicker.platform.pickFiles(
        type: FileType.custom, allowedExtensions: ['png'], withData: true);
      if (picked == null || !mounted) return;
      final file = picked.files.single;
      final data = file.bytes;
      if (data == null || data.isEmpty || data.length > 8 * 1024 * 1024) {
        setState(() => _error = 'Choose a trusted PNG reference smaller than 8 MB.');
        return;
      }
      setState(() { _referenceBytes = data; _referenceName = file.name; _error = null; });
    } catch (_) {
      if (mounted) setState(() => _error = 'Could not open the trusted reference.');
    }
  }

  Future<void> _pickAuthorizedReferences() async {
    try {
      final picked = await FilePicker.platform.pickFiles(
        type: FileType.custom, allowedExtensions: ['jpg', 'jpeg', 'png'],
        allowMultiple: true, withData: true);
      if (picked == null || !mounted) return;
      if (picked.files.isEmpty || picked.files.length > 4 ||
          picked.files.any((f) => f.bytes == null || f.bytes!.isEmpty ||
              f.bytes!.length > 8 * 1024 * 1024)) {
        setState(() => _error = 'Choose 1–4 JPG/PNG reference images, each under 8 MB.');
        return;
      }
      final bytes = <Uint8List>[];
      for (final file in picked.files) {
        final codec = await ui.instantiateImageCodec(file.bytes!);
        final frame = await codec.getNextFrame();
        final megapixels = frame.image.width * frame.image.height;
        frame.image.dispose();
        codec.dispose();
        if (megapixels > 16000000) {
          if (mounted) setState(() => _error = 'Each reference must be 16 MP or smaller.');
          return;
        }
        bytes.add(file.bytes!);
      }
      if (mounted) {
        setState(() {
          _authorizedReferences = bytes;
          _authorizedNames = picked.files.map((f) => f.name).toList();
          _error = null;
        });
      }
    } catch (_) {
      if (mounted) setState(() => _error = 'Could not open authorized references.');
    }
  }

  void _run() {
    final bytes = _bytes;
    final name = _filename;
    if (bytes == null || name == null) return;
    if (_token.text.trim().isEmpty) {
      setState(() => _error = 'Enter the local demo token from your running Flask server.');
      return;
    }
    LocalDemoSession.backendUrl = _backend.text.trim();
    LocalDemoSession.demoToken = _token.text.trim();
    setState(() => _error = null);
    Navigator.push(context, MaterialPageRoute<void>(
      builder: (_) => PipelineScreen(
        isDocument: _isDocument,
        filename: name,
        imageBytes: bytes,
        comparisonPhoto: _isDocument ? _comparisonPhoto : null,
        comparisonFilename: _isDocument ? _comparisonName : null,
        referenceBytes: _isDocument ? _referenceBytes : null,
        authorizedReferences: _isDocument ? _authorizedReferences : const [],
        backendUrl: _backend.text,
        demoToken: _token.text,
      ),
    ));
  }

  @override
  Widget build(BuildContext context) {
    final accent = _isDocument ? AppTheme.primary : AppTheme.magenta;
    return Scaffold(
      appBar: AppBar(title: Text(_isDocument ? 'Document Verification' : 'Analyze Media')),
      body: Center(child: ConstrainedBox(
        constraints: const BoxConstraints(maxWidth: 880),
        child: ListView(padding: const EdgeInsets.all(20), children: [
          Text(_isDocument ? 'Document Verification' : 'AI & deepfake image analysis',
              style: Theme.of(context).textTheme.headlineLarge),
          const SizedBox(height: 8),
          const Text('Local research prototype · findings require human review.',
              style: TextStyle(color: AppTheme.textSub)),
          const SizedBox(height: 22),
          GlassCard(borderColor: accent.withValues(alpha: .35), child: Column(children: [
            if (_bytes != null) ...[
              ClipRRect(borderRadius: BorderRadius.circular(12), child: Image.memory(
                _bytes!, height: 215, width: double.infinity, fit: BoxFit.contain,
                gaplessPlayback: true,
              )),
              const SizedBox(height: 12),
              Text(_filename!, style: const TextStyle(color: AppTheme.text, fontWeight: FontWeight.w600)),
              Text('${(_bytes!.length / (1024 * 1024)).toStringAsFixed(2)} MB · $_width × $_height px',
                  style: const TextStyle(color: AppTheme.textSub)),
            ] else ...[
              Icon(Icons.cloud_upload_outlined, color: accent, size: 46),
              const SizedBox(height: 10),
              Text(_isDocument ? 'Select a document image' : 'Select a media image',
                  style: const TextStyle(color: AppTheme.text)),
              const Text('JPG / JPEG / PNG · up to 8 MB and 16 MP',
                  style: TextStyle(color: AppTheme.textSub)),
            ],
            const SizedBox(height: 16),
            OutlinedButton.icon(onPressed: _pickFile, icon: const Icon(Icons.folder_open_outlined),
                label: Text(_bytes == null ? 'Select image' : 'Replace image')),
            if (_bytes != null) TextButton(onPressed: () => setState(() {
              _bytes = null; _filename = null; _width = null; _height = null;
            }), child: const Text('Remove image')),
          ])),
          const SizedBox(height: 16),
          GlassCard(child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
            const Text('Local backend connection', style: TextStyle(color: AppTheme.text, fontWeight: FontWeight.w700)),
            const SizedBox(height: 12),
            TextField(controller: _backend, keyboardType: TextInputType.url,
                decoration: const InputDecoration(labelText: 'Backend URL', hintText: 'http://127.0.0.1:8001')),
            const SizedBox(height: 12),
            TextField(controller: _token, obscureText: true, enableSuggestions: false,
                autocorrect: false, decoration: const InputDecoration(labelText: 'Local demo token')),
            const SizedBox(height: 8),
            const Text('Token stays in memory only. Android emulator: use http://10.0.2.2:8001 with an explicitly accessible local backend.',
                style: TextStyle(color: AppTheme.textSub, fontSize: 11)),
          ])),
          if (_isDocument) ...[
            const SizedBox(height: 16),
            GlassCard(child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
              const Text('Optional portrait-to-photo similarity · experimental',
                  style: TextStyle(color: AppTheme.text, fontWeight: FontWeight.w700)),
              const SizedBox(height: 8),
              const Text('A separately supplied, authorized face photo is needed ONLY for comparison. Normal document screening requires just one document. No selfie is captured, stored or uploaded to a third-party API.',
                  style: TextStyle(color: AppTheme.textSub, fontSize: 12)),
              const SizedBox(height: 8),
              OutlinedButton.icon(onPressed: _pickComparisonPhoto,
                  icon: const Icon(Icons.face_outlined),
                  label: Text(_comparisonPhoto == null ? 'Add comparison face photo (optional)' : 'Replace comparison photo')),
              if (_comparisonPhoto != null) ...[
                Text('Selected locally: ${_comparisonName ?? 'photo'}',
                    style: const TextStyle(color: AppTheme.textSub, fontSize: 12)),
                TextButton(onPressed: () => setState(() {
                    _comparisonPhoto = null; _comparisonName = null;
                }), child: const Text('Remove comparison photo')),
              ],
            ])),
          ],
          if (_isDocument) ...[
            const SizedBox(height: 16),
            GlassCard(child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
              const Text('Optional trusted document reference · pixel-difference regions',
                style: TextStyle(color: AppTheme.text, fontWeight: FontWeight.w700)),
              const SizedBox(height: 7),
              const Text('Only a separately authorized, aligned PNG of the same fictional document. Different pixels are not proof of unauthorized editing.',
                style: TextStyle(color: AppTheme.textSub, fontSize: 12)),
              OutlinedButton.icon(onPressed: _pickTrustedReference,
                icon: const Icon(Icons.layers_outlined),
                label: Text(_referenceBytes == null ? 'Add trusted PNG (optional)' : 'Replace trusted PNG')),
              if (_referenceBytes != null) ...[
                Text(_referenceName ?? 'Trusted PNG selected',
                  style: const TextStyle(color: AppTheme.textSub)),
                TextButton(onPressed: () => setState(() {
                  _referenceBytes = null; _referenceName = null;
                }), child: const Text('Remove trusted PNG')),
              ],
            ])),
            const SizedBox(height: 16),
            GlassCard(child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
              const Text('Optional authorized reference comparison · experimental',
                style: TextStyle(color: AppTheme.text, fontWeight: FontWeight.w700)),
              const SizedBox(height: 7),
              const Text('Choose up to four authorized JPG/PNG images. Compares only within this request; no identity search or stored gallery. Similarity is not proof of duplication.',
                style: TextStyle(color: AppTheme.textSub, fontSize: 12)),
              OutlinedButton.icon(onPressed: _pickAuthorizedReferences,
                icon: const Icon(Icons.collections_outlined),
                label: Text(_authorizedReferences.isEmpty ? 'Add reference images (optional)' : 'Replace reference set')),
              if (_authorizedReferences.isNotEmpty) ...[
                Text('${_authorizedNames.length} images selected',
                  style: const TextStyle(color: AppTheme.textSub)),
                TextButton(onPressed: () => setState(() {
                  _authorizedReferences = []; _authorizedNames = [];
                }), child: const Text('Remove reference set')),
              ],
            ])),
          ],
          if (_isDocument) ...[
            const SizedBox(height: 20),
            Text('Document criteria · research prototype', style: Theme.of(context).textTheme.titleLarge),
            const SizedBox(height: 8),
            const Text('Criteria switches are disabled: this backend does not support selecting individual checks.',
                style: TextStyle(color: AppTheme.textSub, fontSize: 12)),
            const SizedBox(height: 12),
            const _CriterionCard(
              title: 'OCR Extraction & MRZ', accent: AppTheme.primary,
              icon: Icons.text_fields_outlined, available: true,
              description: 'Text recognition, supported labelled fields, expiry OCR and TD3 passport MRZ consistency checks.',
              checks: ['OCR and labelled fields', 'Spatial expiry extraction (when available)', 'Passport TD3 MRZ checksums'],
            ),
            const SizedBox(height: 10),
            const _CriterionCard(
              title: 'Portrait & optional face comparison', accent: AppTheme.magenta,
              icon: Icons.face_outlined, available: true,
              description: 'Portrait visibility runs on documents. Optional separate face-photo comparison runs only when you supply a photo; no identity verdict.',
              checks: ['Portrait visibility: experimental', 'Consented face-photo similarity: optional research', 'Identity verification: not established'],
            ),
            const SizedBox(height: 10),
            const _CriterionCard(
              title: 'Tampering evidence & region review', accent: AppTheme.amber,
              icon: Icons.manage_search_outlined, available: true,
              description: 'Locates OCR/MRZ-disputed printed fields on one document, when independently corroborated. Does NOT detect standalone pixel forgery.',
              checks: ['Locate corroborated printed-field discrepancies', 'Optional aligned PNG pixel-difference regions', 'Standalone pixel forgery detection: unvalidated'],
            ),
          ],
          if (_error != null) ...[
            const SizedBox(height: 14),
            Text(_error!, style: const TextStyle(color: AppTheme.danger)),
          ],
          const SizedBox(height: 22),
          FilledButton.icon(onPressed: _bytes == null ? null : _run,
              icon: const Icon(Icons.play_arrow_rounded),
              label: Text(_isDocument ? 'Screen document for review' : 'Analyze media'),
              style: FilledButton.styleFrom(minimumSize: const Size.fromHeight(54),
                backgroundColor: accent, foregroundColor: AppTheme.background)),
          const SizedBox(height: 12),
          const Text('These results do not establish identity, authenticity, or fraud.',
              textAlign: TextAlign.center, style: TextStyle(color: AppTheme.textSub, fontSize: 12)),
        ]),
      )),
    );
  }
}

class _CriterionCard extends StatelessWidget {
  final String title, description;
  final Color accent;
  final IconData icon;
  final bool available;
  final List<String> checks;
  const _CriterionCard({required this.title, required this.description, required this.accent,
    required this.icon, required this.available, required this.checks});

  @override
  Widget build(BuildContext context) => GlassCard(
    borderColor: accent.withValues(alpha: .3),
    padding: EdgeInsets.zero,
    child: ExpansionTile(
      leading: Icon(icon, color: accent),
      title: Text(title, style: const TextStyle(color: AppTheme.text, fontWeight: FontWeight.w700, fontSize: 14)),
      subtitle: Text(available ? 'Available · always runs' : 'Not implemented',
          style: TextStyle(color: available ? AppTheme.success : AppTheme.amber, fontSize: 11)),
      childrenPadding: const EdgeInsets.fromLTRB(16, 0, 16, 16),
      children: [
        Align(alignment: Alignment.centerLeft,
          child: Text(description, style: const TextStyle(color: AppTheme.textSub))),
        const SizedBox(height: 8),
        ...checks.map((check) => Align(alignment: Alignment.centerLeft,
          child: Padding(padding: const EdgeInsets.symmetric(vertical: 3), child: Text('• $check',
              style: const TextStyle(color: AppTheme.textSub, fontSize: 12))))),
      ],
    ),
  );
}
