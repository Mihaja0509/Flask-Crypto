from flask import Flask, request, jsonify
from vaderSentiment.vaderSentiment import SentimentIntensityAnalyzer


app = Flask(__name__)
analyzer = SentimentIntensityAnalyzer()


@app.route('/analyze', methods=['POST'])
def analyze_sentiment():

    data = request.get_json()
    if not data or 'text' not in data:

        return jsonify({'error': 'Données invalides. La clé "text" est requise.'}), 400

    text_to_analyze = data['text']

    sentiment_scores = analyzer.polarity_scores(text_to_analyze)

    compound_score = sentiment_scores['compound']

    return jsonify({
        'text': text_to_analyze,
        'sentiment_scores': sentiment_scores
    })

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, debug=True)
