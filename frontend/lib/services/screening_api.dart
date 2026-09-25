import 'dart:async';
import 'dart:convert';
import 'dart:typed_data';
import 'package:http/http.dart' as http;

/// A local research-only API client. The demo token is held in memory, never
/// embedded in the app, stored in history, or printed in diagnostics.
class ScreeningApi {
  static const maxImageBytes = 8 * 1024 * 1024;
  static const requestTimeout = Duration(seconds: 90);

  static Uri _endpoint(String baseUrl, String path) {
    final base = Uri.tryParse(baseUrl.trim());
    if (base == null ||
        !['http', 'https'].contains(base.scheme) ||
        base.host.isEmpty ||
        base.userInfo.isNotEmpty ||
        base.hasQuery ||
        base.hasFragment ||
        (base.path.isNotEmpty && base.path != '/')) {
      throw const ScreeningException('Enter a valid backend URL, such as http://127.0.0.1:8001.');
    }
    // Never send a bearer token over plain HTTP to an arbitrary remote host.
    if (base.scheme == 'http' &&
        !['localhost', '127.0.0.1', '10.0.2.2'].contains(base.host)) {
      throw const ScreeningException('Use HTTPS for a non-local backend URL.');
    }
    return base.replace(path: path);
  }

  static Future<Map<String, dynamic>> analyze({
    required bool document,
    required String backendUrl,
    required String demoToken,
    required Uint8List imageBytes,
    required String filename,
    Uint8List? comparisonPhoto,
    String? comparisonFilename,
    Uint8List? referenceBytes,
    List<Uint8List> authorizedReferences = const [],
  }) async {
    if (demoToken.trim().isEmpty) {
      throw const ScreeningException('Enter your local demo token.');
    }
    if (imageBytes.isEmpty || imageBytes.length > maxImageBytes) {
      throw const ScreeningException('Select a JPG or PNG smaller than 8 MB.');
    }
    final ext = filename.toLowerCase().split('.').last;
    if (!['jpg', 'jpeg', 'png'].contains(ext)) {
      throw const ScreeningException('Only JPG and PNG images are supported.');
    }
    if (referenceBytes != null) {
      if (!document) {
        throw const ScreeningException('Reference comparison is only available for documents.');
      }
      if (referenceBytes.isEmpty || referenceBytes.length > maxImageBytes) {
        throw const ScreeningException('Reference must be a PNG smaller than 8 MB.');
      }
      if (ext != 'png') {
        throw const ScreeningException('Reference comparison requires a PNG document image.');
      }
    }
    if (comparisonPhoto != null) {
      if (!document || comparisonPhoto.isEmpty ||
          comparisonPhoto.length > maxImageBytes || comparisonFilename == null ||
          !['jpg', 'jpeg', 'png'].contains(comparisonFilename.toLowerCase().split('.').last)) {
        throw const ScreeningException('Select a JPG or PNG comparison face photo smaller than 8 MB.');
      }
    }
    if (authorizedReferences.isNotEmpty && (!document || authorizedReferences.length > 4 ||
        authorizedReferences.any((b) => b.isEmpty || b.length > maxImageBytes))) {
      throw const ScreeningException('Use at most four valid authorized reference images (8 MB each).');
    }
    final uri = _endpoint(backendUrl, document ? '/v1/screen' : '/api/v1/detect/image');
    final request = http.MultipartRequest('POST', uri)
      ..headers['Authorization'] = 'Bearer ${demoToken.trim()}'
      ..files.add(http.MultipartFile.fromBytes(
        'image', imageBytes,
        filename: ext == 'png' ? 'screening.png' : 'screening.jpg',
      ));
    if (referenceBytes != null) {
      request.files.add(http.MultipartFile.fromBytes(
        'reference_image', referenceBytes, filename: 'reference.png',
      ));
    }
    if (document && comparisonPhoto != null) {
      request.files.add(http.MultipartFile.fromBytes(
        'comparison_photo', comparisonPhoto,
        filename: comparisonFilename!.toLowerCase().endsWith('.png')
            ? 'comparison.png' : 'comparison.jpg',
      ));
    }
    for (final bytes in authorizedReferences) {
      request.files.add(http.MultipartFile.fromBytes('authorized_reference_images', bytes,
        filename: 'authorized_reference.png'));
    }
    final http.Client client = http.Client();
    try {
      final streamed = await client.send(request).timeout(requestTimeout);
      final response = await http.Response.fromStream(streamed).timeout(requestTimeout);
      Map<String, dynamic> body;
      try {
        final decoded = jsonDecode(response.body);
        if (decoded is! Map<String, dynamic>) throw const FormatException('Invalid JSON object');
        body = decoded;
      } catch (_) {
        throw const ScreeningException('Backend returned an unreadable response.');
      }
      if (response.statusCode == 401) throw const ScreeningException('Unauthorized — check the local demo token.');
      if (response.statusCode != 200) {
        final message = body['error'];
        throw ScreeningException(message is String && message.length < 180
            ? message : 'Screening failed (HTTP ${response.statusCode}).');
      }
      if (document) {
        if (body['ocr'] is! Map || body['document_validation'] is! Map) {
          throw const ScreeningException('Backend screening response is incomplete.');
        }
      } else if (body['image_generation'] is! Map) {
        throw const ScreeningException('Backend image-analysis response is incomplete.');
      }
      return body;
    } on ScreeningException {
      rethrow;
    } on TimeoutException {
      throw const ScreeningException(
          'Backend did not respond within 90 seconds. Check the Flask window; '
          'do not retry until it is healthy.');
    } catch (_) {
      throw const ScreeningException(
          'Cannot reach the backend. Check its URL and that Flask is running.');
    } finally {
      client.close();
    }
  }
  /// No free-form notes or uploaded media; demo token never written to storage.
  static Future<Map<String, dynamic>> submitReview({
    required String backendUrl, required String demoToken,
    required String reviewRef, required String action,
  }) async {
    if (demoToken.trim().isEmpty) throw const ScreeningException('Enter the local demo token.');
    if (!{'reviewed', 'follow_up_required', 'inconclusive'}.contains(action)) {
      throw const ScreeningException('Choose a supported review action.');
    }
    final uri = _endpoint(backendUrl, '/v1/review');
    final client = http.Client();
    try {
      final response = await client.post(uri,
        headers: {'Authorization': 'Bearer ${demoToken.trim()}',
                  'Content-Type': 'application/json'},
        body: jsonEncode({'review_ref': reviewRef, 'action': action}),
      ).timeout(requestTimeout);
      final body = jsonDecode(response.body);
      if (response.statusCode == 401) throw const ScreeningException('Unauthorized — check demo token.');
      if (response.statusCode != 201 || body is! Map<String, dynamic>) {
        throw const ScreeningException('Review action could not be recorded.');
      }
      return body;
    } on ScreeningException {
      rethrow;
    } on TimeoutException {
      throw const ScreeningException('Review audit timed out.');
    } catch (_) {
      throw const ScreeningException('Local review audit is unavailable.');
    } finally { client.close(); }
  }
}

class ScreeningException implements Exception {
  final String message;
  const ScreeningException(this.message);
  @override
  String toString() => message;
}
