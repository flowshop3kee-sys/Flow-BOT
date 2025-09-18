from flask import Flask
from threading import Thread
import os

app = Flask('')

@app.route('/')
def home():
    return "Discord Bot is running! 🤖"

@app.route('/status')
def status():
    return {
        "status": "online",
        "message": "Bot is healthy and running"
    }

def run():
    port = int(os.environ.get('PORT', 8080))
    app.run(host='0.0.0.0', port=port)

def keep_alive():
    """Start the Flask server in a separate thread"""
    t = Thread(target=run)
    t.daemon = True
    t.start()
    print(f"Keep-alive server started on port {os.environ.get('PORT', 8080)}")