from flask import Flask, render_template, request, jsonify
from nlp_engine import HealthcareChatbot

app = Flask(__name__)
bot = HealthcareChatbot()

@app.route('/')
def home():
    return render_template('index.html')

@app.route('/get', methods=['POST'])
def chatbot_response():
    user_input = request.form['msg']
    response = bot.get_response(user_input)
    return jsonify({"response": response})

if __name__ == "__main__":
    app.run(debug=True)
