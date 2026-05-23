import os
from flask import Flask, request, jsonify
from flask import Flask, request, jsonify, send_from_directory
from flask_cors import CORS
from openai import OpenAI
from dotenv import load_dotenv
import psycopg2


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
    return f"Connected to Neon! Database version: 16"



# ... keep your get_db_connection() and save_user_and_trip() functions from before ...

@app.route('/submit-trip', methods=['POST'])
def submit_trip():
    # 1. Parse the incoming JSON data sent by JavaScript
    data = request.get_json()
    
    # 2. Extract the variables using the exact keys used in the JS file
    email = data.get('email')
    name = data.get('name')
    

    # 3. Check to ensure no data is missing
    if not email or not name:
        return jsonify({"status": "error", "message": "Missing required data"}), 400

    # 4. Pass the variables to your database function
    save_user_and_trip(name, email, )

    # 5. Send a confirmation message back to JavaScript
    return jsonify({"status": "success", "message": f"Saved trip for {email}"})



def save_user_and_trip(name, email):
    conn = get_db_connection()
    cur = conn.cursor()
    
    try:
        # 1. Insert or update the user, and get their ID back
        # This updates the 'last_login' time automatically if the email already exists
        cur.execute("""
            INSERT INTO users (name, email, last_login) 
            VALUES (%s, %s, CURRENT_TIMESTAMP)
            ON CONFLICT (email) 
            DO UPDATE SET last_login = CURRENT_TIMESTAMP, name = EXCLUDED.name
            RETURNING id;
        """, (name, email))
        
        user_id = cur.fetchone()[0]
        
        # 2. Save the trip destination for this specific user
        cur.execute("""
            INSERT INTO user_trips (user_id, destination) 
            VALUES (%s, %s);
        """, (user_id, "Paris"))
        
        # Commit changes to the database
        conn.commit()
        print("Successfully saved to database!")
        
    except Exception as e:
        conn.rollback()
        print(f"Error saving to database: {e}")
        
    finally:
        cur.close()
        conn.close()



if __name__ == "__main__":
    app.run(debug=True)
