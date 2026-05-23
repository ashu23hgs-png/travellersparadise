import os
from flask import Flask, request, jsonify
from flask import Flask, request, jsonify, send_from_directory
from flask_cors import CORS
from openai import OpenAI
from dotenv import load_dotenv
import psycopg2


# 1. Fetch the connection string safely from Render's environment
DATABASE_URL = os.environ.get('DATABASE_URL')

def get_db_connection():
    # 2. Connect to your Neon database
    conn = psycopg2.connect(DATABASE_URL)
    return conn

@app.route('/')
def index():
    # Example usage: fetching data from Neon
    conn = get_db_connection()
    cur = conn.cursor()
    cur.execute('SELECT version();')
    db_version = cur.fetchone()
    cur.close()
    conn.close()
    return f"Connected to Neon! Database version: {db_version}"





app = Flask(__name__)
CORS(app)
load_dotenv()
client = OpenAI(
    api_key=os.getenv("OPENAI_API_KEY")
)
@app.route("/")
def home():
    return send_from_directory(".", "index.html")

@app.route("/result.html")
def result():
    return send_from_directory(".", "result.html")

@app.route('/ads.txt')
def ads_txt():
    return send_from_directory(".", "ads.txt")

@app.route("/generate", methods=["POST"])
def generate_trip():

    data = request.json

    city = data.get("city")
    budget = data.get("budget")
    days = data.get("days")

    prompt = f"""
    Create a luxury-looking travel itinerary.

    Destination: {city}
    Budget: ${budget}
    Duration: {days}

    STRICT FORMAT:

    Day 1:
    Morning: ...
    Afternoon: ...
    Evening: ...

    Day 2:
    Morning: ...
    Afternoon: ...
    Evening: ...

    Keep activities realistic and concise.
    """

    response = client.chat.completions.create(
        model="gpt-4o-mini",
        messages=[
            {
                "role": "user",
                "content": prompt
            }
        ]
    )

    plan = response.choices[0].message.content

    return jsonify({
        "plan": plan
    })
# 1. Fetch the connection string safely from Render's environment
DATABASE_URL = os.environ.get('DATABASE_URL')

def get_db_connection():
    # 2. Connect to your Neon database
    conn = psycopg2.connect(DATABASE_URL)
    return conn

@app.route('/')
def index():
    # Example usage: fetching data from Neon
    conn = get_db_connection()
    cur = conn.cursor()
    cur.execute('SELECT version();')
    db_version = cur.fetchone()
    cur.close()
    conn.close()
    return f"Connected to Neon! Database version: {db_version}"

if __name__ == "__main__":
    app.run(debug=True)
