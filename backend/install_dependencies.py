#!/usr/bin/env python3
"""
Script d'installation des dépendances pour Assistant Scolaire
"""
import subprocess
import sys
import os

def run_command(command, description=""):
    """Exécute une commande avec gestion d'erreur"""
    print(f"🔧 {description}...")
    try:
        result = subprocess.run(command, shell=True, check=True, 
                              capture_output=True, text=True)
        print(f"✅ {description} - Succès")
        return True
    except subprocess.CalledProcessError as e:
        print(f"❌ {description} - Erreur: {e.stderr}")
        return False

def install_basic_requirements():
    """Installation des dépendances de base"""
    basic_packages = [
        "flask==2.3.3",
        "flask-jwt-extended==4.5.3", 
        "flask-mysqldb==1.0.1",
        "flask-cors==4.0.0",
        "mysql-connector-python==8.2.0",
        "python-dotenv==1.0.0",
        "colorlog==6.8.0"
    ]
    
    for package in basic_packages:
        if not run_command(f"pip install {package}", f"Installation de {package}"):
            print(f"⚠️ Échec installation {package} - continuons...")

def install_optional_requirements():
    """Installation des dépendances optionnelles"""
    optional_packages = [
        ("together", "LLM Together.ai"),
        ("tiktoken", "Tokenizer OpenAI"), 
        ("langchain", "Framework Langchain"),
        ("langchain-community", "Langchain Community"),
        ("openai", "Client OpenAI")
    ]
    
    print("\n📦 Installation des packages optionnels...")
    for package, description in optional_packages:
        run_command(f"pip install {package}", f"{description}")

def create_env_template():
    """Crée un template .env si inexistant"""
    env_file = ".env"
    if not os.path.exists(env_file):
        env_template = """# Configuration MySQL
MYSQL_HOST=localhost
MYSQL_PORT=3306
MYSQL_USER=root
MYSQL_PASSWORD=your_password
MYSQL_DATABASE=assistant_scolaire

# Configuration JWT
JWT_SECRET_KEY=your-super-secret-jwt-key-change-this

# Configuration Together.ai (optionnel)
TOGETHER_API_KEY=your-together-api-key

# Configuration OpenAI (optionnel) 
OPENAI_API_KEY=your-openai-api-key
"""
        try:
            with open(env_file, 'w') as f:
                f.write(env_template)
            print(f"✅ Fichier {env_file} créé - Veuillez le configurer!")
        except Exception as e:
            print(f"❌ Erreur création {env_file}: {e}")

def test_imports():
    """Test les imports principaux"""
    print("\n🧪 Test des imports...")
    
    imports_to_test = [
        ("flask", "Flask"),
        ("mysql.connector", "MySQL Connector"),
        ("dotenv", "Python Dotenv"),
        ("flask_jwt_extended", "Flask JWT Extended"),
        ("flask_cors", "Flask CORS")
    ]
    
    success_count = 0
    for module, name in imports_to_test:
        try:
            __import__(module)
            print(f"✅ {name} - OK")
            success_count += 1
        except ImportError:
            print(f"❌ {name} - Manquant")
    
    # Test imports optionnels
    optional_imports = [
        ("together", "Together.ai"),
        ("tiktoken", "Tiktoken"),
        ("langchain", "Langchain")
    ]
    
    print("\n🔍 Test des imports optionnels...")
    for module, name in optional_imports:
        try:
            __import__(module)
            print(f"✅ {name} - Disponible")
        except ImportError:
            print(f"⚠️ {name} - Non disponible (optionnel)")
    
    print(f"\n📊 Résultat: {success_count}/{len(imports_to_test)} imports essentiels réussis")
    return success_count == len(imports_to_test)

def main():
    print("🚀 Installation des dépendances Assistant Scolaire\n")
    
    # Mise à jour pip
    run_command("python -m pip install --upgrade pip", "Mise à jour pip")
    
    # Installation des dépendances de base
    print("\n📦 Installation des dépendances essentielles...")
    install_basic_requirements()
    
    # Installation des dépendances optionnelles
    install_optional_requirements()
    
    # Création du fichier .env
    print("\n⚙️ Configuration...")
    create_env_template()
    
    # Test des imports
    if test_imports():
        print("\n🎉 Installation terminée avec succès!")
        print("\n📋 Prochaines étapes:")
        print("1. Configurez le fichier .env avec vos paramètres")
        print("2. Créez votre base de données MySQL")
        print("3. Lancez l'application avec: python app.py")
    else:
        print("\n⚠️ Installation terminée avec des avertissements")
        print("Certaines dépendances optionnelles peuvent manquer")

if __name__ == "__main__":
    main()