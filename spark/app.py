from flask import Flask, render_template, request
from flask_cors import CORS
from spark.chatbot import get_bot_response
from dotenv import load_dotenv
load_dotenv()  

app = Flask(__name__)
CORS(app)

@app.route('/')
def home():
    return render_template('index.html')

@app.route('/api/chat', methods=['POST'])
def chat():
    if not request.is_json:
        return {'error': 'Content-Type must be application/json'}, 400
    
    user_message = request.json.get('message', '')
    state = request.json.get('state', {})
    
    if not user_message:
        return {'error': 'No message provided'}, 400
    
    response, new_state = get_bot_response(user_message, state)
    
    return {
        'response': response,
        'state': new_state
    }

if __name__ == '__main__':
    app.run(debug=True)