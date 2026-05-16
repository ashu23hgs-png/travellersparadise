import os
from flask import Flask, request, jsonify
from flask_cors import CORS
from openai import OpenAI
from dotenv import load_dotenv


app = Flask(__name__)
CORS(app)
load_dotenv()
@app.route("/")
def home():
    return "Traveller's Paradise Backend Running Successfully!"
client = OpenAI(
    api_key=os.getenv("OPENAI_API_KEY")
)

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


if __name__ == "__main__":
    app.run(debug=True)
