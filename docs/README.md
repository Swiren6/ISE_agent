structure du Projet Assistant Scolaire
assistant_scolaire/
├── backend/
│   ├── app.py                    # Serveur Flask principal
│   ├── requirements.txt          # Dépendances Python
│   ├── .env                      # Variables d'environnement
│   ├── config/
│   │   └── database.py           # Configuration base de données
│   ├── models/
│   │   ├── user.py               # Modèle utilisateur
│   │   └── message.py            # Modèle message
│   ├── routes/
│   │   ├── auth.py               # Routes d'authentification
│   │   └── agent.py               # Routes de chat
│   ├── services/
│   │   ├── auth_service.py       # Service d'authentification
│   │   └── sql_assistant.py     # Agent SQL avec LLM (ancien agent.py)
|   ├──agent/
│   │   ├──assistant.py
│   │   ├──cache_manager.py
│   │   ├──llm_utils.py
│   │   ├──sql_query_cache.json
│   │   ├──templates_questions.json
│   │   ├── prompts/
|   |   |   ├── domain_description.json
|   |   |   ├── domain_tables_mapping.json
|   |   |   ├── relation.txt
│   │   └── template_matcher
|   |   |   ├── matcher.py
│   └── utils/
│       ├── jwt_utils.py          # Utilitaires JWT
│       └── sql_utils.py          # Utilitaires SQL
├── frontend/
│   ├── lib/
│   │   ├── main.dart
│   │   ├── models/
│   │   │   ├── user_model.dart
│   │   │   └── message_model.dart
│   │   ├── screens/
│   │   │   ├── login_screen.dart
│   │   │   ├── chat_screen.dart
│   │   │   └── home_screen.dart
│   │   ├── services/
│   │   │   ├── auth_service.dart
│   │   │   ├── api_service.dart
│   │   │   └── storage_service.dart
│   │   ├── widgets/
│   │   │   ├── custom_appbar.dart
│   │   │   ├── message_bubble.dart
│   │   │   └── sidebar_menu.dart
│   │   └── utils/
│   │       ├── constants.dart
│   │       └── theme.dart
│   ├── pubspec.yaml
│   ├── assets/
│   │   └── logo.png
│   └── android/
└── docs/
    ├── API.md
    ├── INSTALL.md
    └── README.md