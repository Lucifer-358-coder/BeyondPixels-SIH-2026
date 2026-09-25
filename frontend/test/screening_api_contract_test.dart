import 'dart:typed_data';
import 'package:flutter_test/flutter_test.dart';
import 'package:beyond_pixals_ui/services/screening_api.dart';

void main() {
  final fixture = Uint8List.fromList([1, 2, 3]);

  test('rejects missing token without sending a request', () async {
    await expectLater(
      ScreeningApi.analyze(document: true, backendUrl: 'http://127.0.0.1:8001',
          demoToken: '', imageBytes: fixture, filename: 'fictional.png'),
      throwsA(isA<ScreeningException>()),
    );
  });

  test('does not attach a reference to media analysis', () async {
    await expectLater(
      ScreeningApi.analyze(document: false, backendUrl: 'http://127.0.0.1:8001',
          demoToken: 'fixture-only', imageBytes: fixture, filename: 'sample.png',
          referenceBytes: fixture),
      throwsA(isA<ScreeningException>().having(
          (error) => error.message, 'message', contains('only available for documents'))),
    );
  });

  test('paired comparison requires PNG document', () async {
    await expectLater(
      ScreeningApi.analyze(document: true, backendUrl: 'http://127.0.0.1:8001',
          demoToken: 'fixture-only', imageBytes: fixture, filename: 'sample.jpg',
          referenceBytes: fixture),
      throwsA(isA<ScreeningException>().having(
          (error) => error.message, 'message', contains('PNG document'))),
    );
  });

  test('never sends a bearer token via remote plain HTTP', () async {
    await expectLater(
      ScreeningApi.analyze(document: false, backendUrl: 'http://example.com:8001',
          demoToken: 'fixture-only', imageBytes: fixture, filename: 'sample.png'),
      throwsA(isA<ScreeningException>().having(
          (error) => error.message, 'message', contains('HTTPS'))),
    );
  });
}
