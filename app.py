from flask import Flask, request, jsonify
from vaderSentiment.vaderSentiment import SentimentIntensityAnalyzer
import firebase_admin
from firebase_admin import credentials, messaging

# --- 1. Initialisation de Firebase Admin ---
# IMPORTANT: Remplacez 'votre-fichier-de-service.json' par le vrai nom du fichier
# que vous avez téléchargé depuis la console Google.
try:
    cred = credentials.Certificate("gamerealese-385cbdca-4dc211eac9bd.json")
    firebase_admin.initialize_app(cred)
    print("Firebase Admin SDK initialisé avec succès.")
except Exception as e:
    print(f"ERREUR: Impossible d'initialiser Firebase Admin SDK. Vérifiez le chemin du fichier JSON. Erreur: {e}")
# ---------------------------------------------


app = Flask(__name__)
analyzer = SentimentIntensityAnalyzer()


# Votre endpoint existant, on n'y touche pas
@app.route('/analyze', methods=['POST'])
def analyze_sentiment():
    data = request.get_json()
    if not data or 'text' not in data:
        return jsonify({'error': 'Données invalides. La clé "text" est requise.'}), 400

    text_to_analyze = data['text']
    sentiment_scores = analyzer.polarity_scores(text_to_analyze)
    return jsonify({
        'text': text_to_analyze,
        'sentiment_scores': sentiment_scores
    })

# --- 2. Notre nouvelle fonction pour envoyer des notifications ---
def send_push_notification(token, title, body):
    if not token:
        print("Erreur : Token FCM manquant pour l'envoi.")
        return False
    
    message = messaging.Message(
        notification=messaging.Notification(title=title, body=body),
        token=token,
    )

    try:
        response = messaging.send(message)
        print(f"Notification envoyée avec succès : {response}")
        return True
    except Exception as e:
        print(f"Erreur lors de l'envoi de la notification : {e}")
        return False
# ----------------------------------------------------------------

# --- 3. Une route spéciale pour tester l'envoi ---
@app.route('/test-push', methods=['GET'])
def test_push_notification():
    # On récupère le token du téléphone depuis l'URL
    # Exemple d'URL : https://votre-app.onrender.com/test-push?token=TOKEN_DU_TELEPHONE
    fcm_token = request.args.get('token')
    
    if not fcm_token:
        return "Erreur : Veuillez fournir un token dans l'URL (ex: ?token=...)", 400

    print(f"Tentative d'envoi d'une notification de test au token : {fcm_token[:15]}...")
    
    success = send_push_notification(
        token=fcm_token,
        title="Notification de Test ✅",
        body="Si vous recevez ceci, la configuration est parfaite !"
    )

    if success:
        return "Notification de test envoyée avec succès !", 200
    else:
        return "Échec de l'envoi de la notification. Vérifiez les logs du serveur.", 500
# ----------------------------------------------------


if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, debug=True)