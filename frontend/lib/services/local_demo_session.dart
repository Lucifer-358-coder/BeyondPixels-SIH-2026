/// Runtime-only connection settings shared by both analysis screens.
/// Never persist, print, or bundle the operator's bearer token.
class LocalDemoSession {
  static String backendUrl = 'http://127.0.0.1:8001';
  static String demoToken = '';
}
