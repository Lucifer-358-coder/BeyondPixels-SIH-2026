import 'package:flutter/foundation.dart';

/// Deliberately transient: only filename, type, status and time are retained.
/// No token, uploaded image, OCR identity field, or backend raw JSON is stored.
class SessionEntry {
  final String filename;
  final bool isDocument;
  final String status;
  final DateTime time;
  const SessionEntry(this.filename, this.isDocument, this.status, this.time);
}

class SessionHistory extends ChangeNotifier {
  SessionHistory._();
  static final SessionHistory instance = SessionHistory._();
  final List<SessionEntry> _items = [];
  List<SessionEntry> get items => List.unmodifiable(_items);
  void add(SessionEntry entry) {
    _items.insert(0, entry);
    if (_items.length > 25) _items.removeLast();
    notifyListeners();
  }
  void clear() {
    _items.clear();
    notifyListeners();
  }
}
