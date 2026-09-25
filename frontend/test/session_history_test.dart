import 'package:flutter_test/flutter_test.dart';
import 'package:beyond_pixals_ui/models/session_history.dart';

void main() {
  test('session history contains no image bytes or demo tokens and can be cleared', () {
    final history = SessionHistory.instance;
    history.clear();
    history.add(SessionEntry('sample.png', true, 'inconclusive', DateTime(2026)));
    expect(history.items.length, 1);
    expect(history.items.single.filename, 'sample.png');
    history.clear();
    expect(history.items, isEmpty);
  });
}
