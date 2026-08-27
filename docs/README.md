# ISE Agent 🎓🤖

An AI-powered school management assistant that lets students and administrators query academic data using **natural language**. Built with a Flask REST API backend and a Flutter mobile frontend, the system routes questions through an LLM and converts them into optimized SQL queries in real time.

---

## Features

- 🧠 **Natural Language → SQL** — Ask questions like *"What are my grades this semester?"* and get instant answers from the database
- 📂 **Multi-domain routing** — Handles student records, finances, enrollments, and pedagogy through specialized prompt templates
- 📄 **PDF document generation** — Automatically produces academic attestations and grade bulletins
- 🔐 **JWT Authentication** — Secure login and role-based access control
- ⚡ **SQL Query Cache** — Optimized repeated requests for faster responses
- 📱 **Flutter Mobile Frontend** — Cross-platform mobile interface with clean UI components

---

## Tech Stack

| Layer | Technology |
|---|---|
| Backend | Python · Flask |
| AI / NLP | LLM integration · Prompt engineering |
| Database | SQL (ORM models) |
| Auth | JWT |
| Document generation | PDF utilities |
| Frontend | Flutter · Dart |
| API communication | REST |

---

## Project Structure

```
ISE_agent/
├── backend/
│   ├── src/
│   │   ├── models/          # ORM database models
│   │   ├── routes/          # API route handlers
│   │   ├── agents/          # LLM + SQL agent logic
│   │   ├── prompts/         # Domain-specific prompt templates
│   │   ├── cache/           # Query caching layer
│   │   └── pdf/             # PDF generation utilities
│   └── config/              # Environment configuration
└── frontend/
    ├── lib/
    │   ├── screens/         # App screens
    │   ├── services/        # API client & local storage
    │   ├── widgets/         # Reusable UI components
    │   └── theme/           # App theming
    └── pubspec.yaml
```

---

## Getting Started

### Prerequisites

- Python 3.10+
- Flutter SDK
- A running SQL database
- LLM API key (configured via environment variables)

### Backend Setup

```bash
# Clone the repository
git clone https://github.com/Swiren6/ISE_agent.git
cd ISE_agent/backend

# Install dependencies
pip install -r requirements.txt

# Configure environment variables
cp .env.example .env
# Edit .env with your database URL and LLM API key

# Run the server
flask run
```

### Frontend Setup

```bash
cd frontend

# Install Flutter dependencies
flutter pub get

# Run the app
flutter run
```

---

## How It Works

1. The user submits a natural language question via the mobile app
2. The backend classifies the query domain (student records, finances, etc.)
3. A domain-specific prompt template is filled and sent to the LLM
4. The LLM generates an SQL query, which is validated and executed
5. The result is formatted and returned to the user
6. Frequently repeated queries are served from the cache

---

## License

This project is licensed under the MIT License.
