import 'package:flutter_test/flutter_test.dart';
import 'package:aes_project/main.dart';

void main() {
  group('MyApp Widget Tests', () {
    testWidgets('Counter increments', (tester) async {
      await tester.pumpWidget(const MyApp());
      expect(find.text('0'), findsOneWidget);
      await tester.tap(find.byIcon(Icons.add));
      await tester.pump();
      expect(find.text('1'), findsOneWidget);
    });

    testWidgets('App title is displayed', (tester) async {
      await tester.pumpWidget(const MyApp());
      expect(find.text('AES Flutter Demo'), findsOneWidget);
    });
  });
}
