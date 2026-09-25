import 'package:flutter/material.dart';
import '../theme/app_theme.dart';
import '../widgets/glass_card.dart';

class ProfileScreen extends StatelessWidget {
  const ProfileScreen({super.key});
  @override
  Widget build(BuildContext context) => Scaffold(
    appBar: AppBar(title: const Text('About & privacy')),
    body: Center(child: ConstrainedBox(constraints: const BoxConstraints(maxWidth: 850),
      child: ListView(padding: const EdgeInsets.all(20), children: [
        GlassCard(child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
          Text('BeyondPixels', style: TextStyle(color: AppTheme.primary,
              fontSize: 22, fontWeight: FontWeight.w700)),
          SizedBox(height: 10),
          Image.asset('assets/branding/beyondpixels_wordmark.png',
            height: 190, width: double.infinity, fit: BoxFit.contain),
          SizedBox(height: 10),
          Text('Local research demonstration · no account is signed in.',
              style: TextStyle(color: AppTheme.textSub)),
        ])),
        SizedBox(height: 14),
        GlassCard(child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
          Text('Privacy', style: TextStyle(color: AppTheme.text, fontWeight: FontWeight.w700)),
          SizedBox(height: 8),
          Text('The demo token is used in memory for requests. Session history keeps only filenames, outcomes and timestamps, and is cleared when the app closes. Uploaded image bytes are sent to your configured backend.',
              style: TextStyle(color: AppTheme.textSub)),
        ])),
        SizedBox(height: 14),
        GlassCard(child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
          Text('Scope', style: TextStyle(color: AppTheme.text, fontWeight: FontWeight.w700)),
          SizedBox(height: 8),
          Text('Document Verification: OCR, TD1/TD2/TD3 MRZ checks, bounded tampering indicators, optional aligned-PNG pixel-difference regions, consented portrait-to-photo similarity and request-scoped authorized image similarity. AI Image Detection is a separate workflow. No identity, forgery or fraud verdict is established. Local demo review actions are logged without images or OCR data; this is not role-based access control or tamper-proof auditing.',
              style: TextStyle(color: AppTheme.textSub)),
        ])),
      ]),
    )),
  );
}
