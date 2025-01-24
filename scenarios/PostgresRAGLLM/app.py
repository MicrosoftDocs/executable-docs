from flask import Flask, request, render_template, make_response
import subprocess
import os
import logging

app = Flask(__name__)

# Configure logging
logging.basicConfig(level=logging.DEBUG)

@app.after_request
def add_header(response):
    response.headers['Content-Type'] = 'text/html'
    return response

@app.route('/', methods=['GET'])
def home():
    logging.debug("Rendering home page")
    return render_template("index.html")

@app.route('/ask', methods=['POST'])
def ask():
    question = request.form['question']
    logging.debug(f"Received question: {question}")
    result = subprocess.run([
        'python3', 'chat.py',
        '--api-key', os.getenv('API_KEY'),
        '--endpoint', os.getenv('ENDPOINT'),
        '--pguser', os.getenv('PGUSER'),
        '--pghost', os.getenv('PGHOST'),
        '--pgpassword', os.getenv('PGPASSWORD'),
        '--pgdatabase', os.getenv('PGDATABASE'),
        '--question', question
    ], capture_output=True, text=True)
    logging.debug(f"Subprocess result: {result}")
    if result.returncode != 0:
        logging.error(f"Subprocess error: {result.stderr}")
        response_text = f"Error: {result.stderr}"
    else:
        response_text = result.stdout
    logging.debug(f"Response: {response_text}")
    return render_template('index.html', response=response_text)

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=8000, debug=True)