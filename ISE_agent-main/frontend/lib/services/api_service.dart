import 'dart:convert';
import 'dart:io';
import 'dart:async';
import 'package:http/http.dart' as http;
import '../utils/constants.dart';

class ApiException implements Exception {
  final String message;
  final int? statusCode;

  ApiException(this.message, [this.statusCode]);

  @override
  String toString() =>
      '$message${statusCode != null ? ' (Code: $statusCode)' : ''}';
}

class ApiService {
  static const String baseUrl = AppConstants.apiBaseUrl;
  static const Duration defaultTimeout = Duration(seconds: 30);

  Map<String, String> _getHeaders(String? token) {
    return {
      'Content-Type': 'application/json; charset=utf-8',
      'Accept': 'application/json',
      if (token != null && token.isNotEmpty) 'Authorization': 'Bearer $token',
    };
  }

  /// Test de connectivité avec le backend
  Future<bool> testConnection() async {
    try {
      final response =
          await get('/health', timeout: const Duration(seconds: 5));
      return response['status'] == 'OK';
    } catch (e) {
      print('❌ Test de connexion échoué: $e');
      return false;
    }
  }

  /// Connexion utilisateur
  Future<Map<String, dynamic>> login(
      String loginIdentifier, String password) async {
    final endpoint = '/login';
    print('🔐 Tentative de connexion pour: $loginIdentifier');

    try {
      final response = await post(
        endpoint,
        {
          'login_identifier': loginIdentifier,
          'password': password,
        },
        timeout: const Duration(seconds: 15),
      );

      print('✅ Connexion réussie');
      return response;
    } on ApiException {
      rethrow;
    } catch (e) {
      print('❌ Erreur de connexion: $e');
      throw ApiException('Erreur lors de la connexion');
    }
  }

  /// Envoi d'une question au chat
  // Dans votre api_service.dart, modifiez la méthode askQuestion pour débugger

Future<Map<String, dynamic>> askQuestion(String question, String token) async {
  final endpoint = '/ask_question';
  final url = Uri.parse('$baseUrl$endpoint');

  print('💬 Envoi de question: $question');
  print('📤 URL: $url');

  final headers = {
    'Content-Type': 'application/json',
    'Authorization': 'Bearer $token',
  };
  final body = jsonEncode({'question': question.trim()});

  try {
    final response = await http
        .post(url, headers: headers, body: body)
        .timeout(const Duration(seconds: 60));

    print('📥 Réponse reçue - Status: ${response.statusCode}');
    return _handleResponse(response);
  } on TimeoutException {
    throw ApiException('Timeout: Le serveur ne répond pas');
  } catch (e) {
    throw ApiException('Erreur technique: ${e.toString()}');
  }
} // <== ICI doit se terminer askQuestion

Map<String, dynamic> _handleResponse(http.Response response) {
  final statusCode = response.statusCode;
  print('🔍 Status Code: $statusCode');
  print('🔍 Body (raw): ${response.body}');

  // Gestion spéciale des erreurs 405
  if (statusCode == 405) {
    throw ApiException(
      'Méthode non autorisée. Vérifiez que le endpoint accepte bien POST.',
      405,
    );
  }

  try {
    return jsonDecode(utf8.decode(response.bodyBytes));
  } on FormatException {
    // Si le backend renvoie du HTML/texte
    throw ApiException(
      'Le serveur a répondu avec un format inattendu: ${response.body}',
      statusCode,
    );
  }
}

  // Requête GET générique
  Future<Map<String, dynamic>> get(
    String endpoint, {
    String? token,
    Duration? timeout,
  }) async {
    try {
      final uri = Uri.parse('$baseUrl$endpoint');
      final headers = _getHeaders(token);

      print('📤 GET: $uri');

      final response = await http
          .get(uri, headers: headers)
          .timeout(timeout ?? defaultTimeout);

      print('📥 Response: ${response.statusCode}');
      return _handleResponse(response);
    } on SocketException {
      throw ApiException('Pas de connexion internet. Vérifiez votre réseau.');
    } on http.ClientException {
      throw ApiException('Impossible de se connecter au serveur.');
    } on TimeoutException {
      throw ApiException('Temps d\'attente dépassé. Le serveur ne répond pas.');
    } catch (e) {
      if (e is ApiException) rethrow;
      throw ApiException('Erreur lors de la requête: ${e.toString()}');
    }
  }

  /// Requête POST générique
  Future<Map<String, dynamic>> post(
    String endpoint,
    Map<String, dynamic> data, {
    String? token,
    Duration? timeout,
  }) async {
    try {
      final uri = Uri.parse('$baseUrl$endpoint');
      final headers = _getHeaders(token);
      final body = jsonEncode(data);

      print('📤 POST: $uri');
      print('📤 Body: $body');

      final response = await http
          .post(uri, headers: headers, body: body)
          .timeout(timeout ?? defaultTimeout);

      print('📥 Response: ${response.statusCode}');
      return _handleResponse(response);
    } on SocketException {
      throw ApiException('Pas de connexion internet. Vérifiez votre réseau.');
    } on http.ClientException {
      throw ApiException('Impossible de se connecter au serveur.');
    } on TimeoutException {
      throw ApiException('Temps d\'attente dépassé. Le serveur ne répond pas.');
    } catch (e) {
      if (e is ApiException) rethrow;
      throw ApiException('Erreur lors de la requête: ${e.toString()}');
    }
  }
}
