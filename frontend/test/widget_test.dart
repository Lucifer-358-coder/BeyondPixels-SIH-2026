import 'package:flutter_test/flutter_test.dart';
import 'package:beyond_pixals_ui/main.dart';

void main() {
  testWidgets('App renders BeyondPixels home', (WidgetTester tester) async {
    await tester.pumpWidget(const BeyondPixelsApp());
    // The app title text appears in the top bar
    expect(find.text('BeyondPixels'), findsOneWidget);
  });
}
