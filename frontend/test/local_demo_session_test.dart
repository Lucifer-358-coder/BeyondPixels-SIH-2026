import 'package:flutter_test/flutter_test.dart';
import 'package:beyond_pixals_ui/services/local_demo_session.dart';

void main() {
  test('both workflows reuse runtime-only demo connection settings', () {
    final originalUrl = LocalDemoSession.backendUrl;
    final originalToken = LocalDemoSession.demoToken;
    try {
      LocalDemoSession.backendUrl = 'http://127.0.0.1:8001';
      LocalDemoSession.demoToken = 'fixture-only-not-a-real-token';
      expect(LocalDemoSession.backendUrl, 'http://127.0.0.1:8001');
      expect(LocalDemoSession.demoToken, 'fixture-only-not-a-real-token');
    } finally {
      LocalDemoSession.backendUrl = originalUrl;
      LocalDemoSession.demoToken = originalToken;
    }
  });
}
