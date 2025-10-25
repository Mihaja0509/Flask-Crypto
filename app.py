from flask import Flask, request, jsonify
from vaderSentiment.vaderSentiment import SentimentIntensityAnalyzer
import firebase_admin
from firebase_admin import credentials, messaging
import requests # Ajouté pour appeler l'API CoinGecko
import json

# --- 1. Initialisation de Firebase Admin ---
# Vous avez déjà bien configuré cette partie.
try:
    cred = credentials.Certificate("gamerealese-385cbdca-4dc211eac9bd.json")
    firebase_admin.initialize_app(cred)
    print("Firebase Admin SDK initialisé avec succès.")
except Exception as e:
    print(f"ERREUR: Impossible d'initialiser Firebase Admin SDK. Erreur: {e}")
# ---------------------------------------------

# --- NOUVEAU : Notre fausse base de données en mémoire ---
# C'est un simple dictionnaire pour l'exemple.
# Dans une vraie application, vous remplacerez ça par une base de données (ex: PostgreSQL sur Render)
# Format: { "token_utilisateur_1": {"favorites": ["bitcoin", "ethereum"]}, "token_utilisateur_2": ... }
REGISTERED_USERS = {}
# ---------------------------------------------------


app = Flask(__name__)
analyzer = SentimentIntensityAnalyzer()


# Votre endpoint existant, on n'y touche pas
@app.route('/analyze', methods=['POST'])
def analyze_sentiment():
    # ... (votre code reste identique) ...
    data = request.get_json()
    if not data or 'text' not in data:
        return jsonify({'error': 'Données invalides. La clé "text" est requise.'}), 400
    text_to_analyze = data['text']
    sentiment_scores = analyzer.polarity_scores(text_to_analyze)
    return jsonify({ 'text': text_to_analyze, 'sentiment_scores': sentiment_scores })

# --- NOUVEAU : Une route pour que l'app Flutter enregistre un utilisateur ---
@app.route('/register', methods=['POST'])
def register_user():
    data = request.get_json()
    if not data or 'token' not in data or 'favorites' not in data:
        return jsonify({'error': 'Données invalides. "token" et "favorites" sont requis.'}), 400
    
    token = data['token']
    favorites = data['favorites'] # ex: ["bitcoin", "ethereum"]
    
    REGISTERED_USERS[token] = {"favorites": favorites}
    
    print(f"Utilisateur enregistré/mis à jour: {token[:15]}... avec {len(favorites)} favoris.")
    print(f"Base de données actuelle: {REGISTERED_USERS}")
    
    return jsonify({'status': 'success', 'message': f'Utilisateur {token[:15]} enregistré.'}), 200
# ----------------------------------------------------------------------

# --- NOUVEAU : La logique de surveillance (le "cerveau") ---
def check_for_alerts():
    print("\n--- Lancement du cycle de vérification des alertes ---")
    if not REGISTERED_USERS:
        print("Aucun utilisateur enregistré. Fin du cycle.")
        return
        
    # On itère sur chaque utilisateur enregistré
    for token, user_data in REGISTERED_USERS.items():
        favorites = user_data.get("favorites", [])
        if not favorites:
            continue
            
        print(f"Vérification des favoris pour l'utilisateur {token[:15]}...")
        # Pour chaque crypto favorite de l'utilisateur
        for crypto_id in favorites:
            try:
                # 1. Récupérer les données fraîches depuis CoinGecko
                api_url = f"https://api.coingecko.com/api/v3/coins/{crypto_id}?localization=false&tickers=false&market_data=true&community_data=false&developer_data=true&sparkline=false"
                response = requests.get(api_url)
                response.raise_for_status()
                crypto_data = response.json()
                
                # 2. Analyser les anomalies (version Python de votre service)
                market_cap = crypto_data.get('market_data', {}).get('market_cap', {}).get('usd', 0)
                commit_count = crypto_data.get('developer_data', {}).get('commit_count_4_weeks', 0)

                # 3. Détecter si une anomalie critique existe
                if market_cap > 50000000 and commit_count < 2:
                    print(f"ALERTE DÉTECTÉE pour {crypto_id} ! Développement stagnant.")
                    send_push_notification(
                        token=token,
                        title=f"🚨 Alerte Anomalie sur {crypto_data.get('name', crypto_id).capitalize()}",
                        body="Une anomalie critique a été détectée: l'activité de développement semble stagnante."
                    )
            except requests.exceptions.RequestException as e:
                print(f"Erreur de réseau en récupérant les données pour {crypto_id}: {e}")
            except Exception as e:
                print(f"Erreur inattendue lors de la vérification de {crypto_id}: {e}")
    print("--- Fin du cycle de vérification ---")


# --- NOUVEAU : Une route pour déclencher le scan manuellement (pour le test et le Cron Job) ---
@app.route('/trigger-check', methods=['GET'])
def trigger_check():
    check_for_alerts()
    return "Vérification des alertes terminée. Consultez les logs du serveur.", 200
# ------------------------------------------------------------------------------------


# Votre fonction d'envoi de notification (inchangée)
def send_push_notification(token, title, body):
    # ... (votre code reste identique) ...
    if not token:
        print("Erreur : Token FCM manquant pour l'envoi.")
        return False
    message = messaging.Message( notification=messaging.Notification(title=title, body=body), token=token,)
    try:
        response = messaging.send(message)
        print(f"Notification envoyée avec succès : {response}")
        return True
    except Exception as e:
        print(f"Erreur lors de l'envoi de la notification : {e}")
        return False

# Votre route de test (inchangée)
@app.route('/test-push', methods=['GET'])
def test_push_notification():
    # ... (votre code reste identique) ...
    fcm_token = request.args.get('token')
    if not fcm_token:
        return "Erreur : Veuillez fournir un token dans l'URL (ex: ?token=...)", 400
    print(f"Tentative d'envoi d'une notification de test au token : {fcm_token[:15]}...")
    success = send_push_notification(token=fcm_token, title="Notification de Test ✅", body="Si vous recevez ceci, la configuration est parfaite !")
    if success:
        return "Notification de test envoyée avec succès !", 200
    else:
        return "Échec de l'envoi de la notification. Vérifiez les logs du serveur.", 500


if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, debug=True)
