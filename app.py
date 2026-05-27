import json
import os
from flask import Flask, Response, request, jsonify, send_from_directory
from flask_cors import CORS
from openai import OpenAI
from dotenv import load_dotenv
try:
    import psycopg2
except ImportError:
    psycopg2 = None


app = Flask(__name__)
# Local dev CORS: Live Server (5500) -> Flask (5000)
CORS(
    app,
    resources={
        r"/*": {
            "origins": [
                "http://127.0.0.1:5500",
                "http://localhost:5500",
                "http://127.0.0.1:5000",
                "http://localhost:5000",
            ],
            "methods": ["GET", "POST", "OPTIONS"],
            "allow_headers": ["Content-Type"],
        }
    },
)
load_dotenv()
GROQ_API_KEY = (
    os.getenv("GROQ_API_KEY")
    or os.getenv("Groq_API_KEY")
    or os.getenv("groq_api_key")
)
GROQ_BASE_URL = "https://api.groq.com/openai/v1"
GROQ_MODEL = os.getenv("GROQ_MODEL", "llama-3.3-70b-versatile")

def create_ai_client():
    if not GROQ_API_KEY:
        raise RuntimeError("GROQ_API_KEY is not configured in .env")

    return OpenAI(
        api_key=GROQ_API_KEY,
        base_url=GROQ_BASE_URL
    )
@app.route("/")
def home():
    return send_from_directory(".", "index.html")

@app.route("/index.html")
def index_page():
    return send_from_directory(".", "index.html")

@app.route("/about.html")
def about_page():
    return send_from_directory(".", "about.html")

@app.route("/explore-destinations.html")
def explore_destinations_page():
    return send_from_directory(".", "explore-destinations.html")

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

    try:
        ai_client = create_ai_client()
    except RuntimeError as error:
        return jsonify({"error": str(error)}), 500

    response = ai_client.chat.completions.create(
        model=GROQ_MODEL,
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

def get_ai_json(prompt):
    ai_client = create_ai_client()

    response = ai_client.chat.completions.create(
        model=GROQ_MODEL,
        response_format={"type": "json_object"},
        messages=[
            {
                "role": "system",
                "content": (
                    "You are a modern travel intelligence assistant for Traveller's Paradise. "
                    "Return only valid JSON. Keep advice practical, specific, concise, and safe."
                )
            },
            {"role": "user", "content": prompt}
        ],
        temperature=0.7,
    )

    content = response.choices[0].message.content
    return json.loads(content)

def fallback_destination_analytics(destination, reason=None):
    clean_destination = destination.strip().title() or "Your Destination"

    return {
        "destination": clean_destination,
        "summary": (
            f"{clean_destination} is ready for a flexible travel plan with a mix of highlights, "
            "local flavor, and practical day-to-day planning. These recommendations are a reliable "
            "fallback while live Groq AI analytics are unavailable."
        ),
        "quick_stats": [
            {"label": "Best For", "value": "Culture, food, photos"},
            {"label": "Trip Length", "value": "3 to 5 days"},
            {"label": "Daily Budget", "value": "$45 to $180"},
            {"label": "Travel Style", "value": "Balanced explorer"}
        ],
        "packing_tips": [
            {"title": "Layer Smart", "detail": "Pack breathable basics, one warmer layer, and a light rain shell so you can adapt quickly."},
            {"title": "Comfort First", "detail": "Bring broken-in walking shoes because most memorable travel days involve more steps than expected."},
            {"title": "Day Kit", "detail": "Carry a power bank, refillable bottle, copies of documents, sunscreen, and a small medicine pouch."},
            {"title": "Local Ready", "detail": "Keep a little cash, an offline map, and a translation app downloaded before you arrive."}
        ],
        "best_time_to_visit": [
            {"season": "Spring", "reason": "Comfortable weather, easier sightseeing, and good conditions for outdoor neighborhoods and viewpoints."},
            {"season": "Autumn", "reason": "Milder temperatures, attractive light for photos, and usually fewer crowds than peak holiday periods."},
            {"season": "Shoulder Season", "reason": "Often gives the best balance of prices, weather, and hotel availability."}
        ],
        "safety_advice": [
            {"title": "Stay Area-Aware", "detail": "Check recent local guidance for neighborhoods, late-night transport, and common tourist scams."},
            {"title": "Protect Essentials", "detail": "Use a crossbody bag or inner pocket for passport, cards, and phone in crowded areas."},
            {"title": "Plan Transport", "detail": "Prefer official taxis, rideshare apps, hotel-arranged transfers, or well-reviewed public routes at night."},
            {"title": "Share Your Plan", "detail": "Send your hotel address and rough daily route to someone you trust when exploring solo."}
        ],
        "local_food_recommendations": [
            {"dish": "Street Food Classics", "why": "They are usually affordable, fast, and a great way to understand everyday local taste."},
            {"dish": "Regional Breakfast", "why": "Morning dishes often reveal the most authentic side of a place before tourist crowds arrive."},
            {"dish": "Market Snacks", "why": "Food markets let you sample several local flavors without committing to one large meal."},
            {"dish": "Family-Run Restaurant", "why": "Small local restaurants are often better value and more memorable than main-square dining."}
        ],
        "budget_guide": [
            {"tier": "Budget", "daily_cost": "$45-$80", "notes": "Hostels or simple stays, public transport, markets, and free or low-cost attractions."},
            {"tier": "Comfort", "daily_cost": "$90-$150", "notes": "Good mid-range hotel, paid experiences, cafe meals, and occasional taxis."},
            {"tier": "Luxury", "daily_cost": "$180+", "notes": "Boutique stays, private transfers, guided tours, fine dining, and premium experiences."}
        ],
        "source": "fallback",
        "notice": reason or "Live Groq AI analytics are unavailable right now."
    }

def pdf_escape(text):
    return str(text or "").encode("latin-1", "replace").decode("latin-1").replace("\\", "\\\\").replace("(", "\\(").replace(")", "\\)")

def wrap_pdf_text(text, width=92):
    words = str(text or "").split()
    lines = []
    current = ""

    for word in words:
        if len(current) + len(word) + 1 > width:
            if current:
                lines.append(current)
            current = word
        else:
            current = f"{current} {word}".strip()

    if current:
        lines.append(current)

    return lines or [""]

def analytics_to_pdf_bytes(data):
    destination = data.get("destination") or "Destination"
    lines = [
        ("title", f"{destination} Travel Analytics"),
        ("small", "Generated by Traveller's Paradise"),
        ("blank", ""),
        ("body", data.get("summary", "")),
        ("blank", "")
    ]

    if data.get("quick_stats"):
        lines.append(("section", "Quick Stats"))
        for stat in data.get("quick_stats", []):
            lines.append(("body", f"{stat.get('label', '')}: {stat.get('value', '')}"))
        lines.append(("blank", ""))

    sections = [
        ("Packing Tips", data.get("packing_tips", []), "title", "detail"),
        ("Best Time to Visit", data.get("best_time_to_visit", []), "season", "reason"),
        ("Safety Advice", data.get("safety_advice", []), "title", "detail"),
        ("Local Food Recommendations", data.get("local_food_recommendations", []), "dish", "why"),
        ("Budget Guide", data.get("budget_guide", []), "tier", "daily_cost"),
        ("Budget Notes", data.get("budget_guide", []), "tier", "notes")
    ]

    for section_title, items, title_key, detail_key in sections:
        if not items:
            continue

        lines.append(("section", section_title))
        for item in items:
            heading = item.get(title_key, "")
            detail = item.get(detail_key, "")
            lines.append(("body", f"{heading}: {detail}"))
        lines.append(("blank", ""))

    pages = []
    current_page = []
    y = 792

    for kind, text in lines:
        font_size = 22 if kind == "title" else 15 if kind == "section" else 9 if kind == "small" else 11
        line_height = 26 if kind == "title" else 20 if kind == "section" else 13
        wrapped = [""] if kind == "blank" else wrap_pdf_text(text, 78 if kind == "title" else 92)

        for wrapped_line in wrapped:
            if y < 54:
                pages.append(current_page)
                current_page = []
                y = 792

            current_page.append((kind, font_size, y, wrapped_line))
            y -= line_height

    if current_page:
        pages.append(current_page)

    objects = [
        "<< /Type /Catalog /Pages 2 0 R >>",
        "",
        "<< /Type /Font /Subtype /Type1 /BaseFont /Helvetica >>"
    ]

    page_object_ids = []
    content_object_ids = []

    for page in pages:
        page_object_ids.append(len(objects) + 1)
        objects.append("")
        content_object_ids.append(len(objects) + 1)

        commands = ["0.031 0.031 0.063 rg 0 0 595 842 re f"]
        for kind, font_size, y, text in page:
            if kind == "title":
                color = "0.949 0.929 0.902"
            elif kind == "section":
                color = "0.910 0.784 0.478"
            elif kind == "small":
                color = "0.443 0.839 0.788"
            else:
                color = "0.808 0.784 0.745"

            if text:
                commands.append(f"BT /F1 {font_size} Tf {color} rg 50 {y} Td ({pdf_escape(text)}) Tj ET")

        stream = "\n".join(commands)
        objects.append(f"<< /Length {len(stream.encode('latin-1'))} >>\nstream\n{stream}\nendstream")

    kids = " ".join(f"{page_id} 0 R" for page_id in page_object_ids)
    objects[1] = f"<< /Type /Pages /Kids [{kids}] /Count {len(page_object_ids)} >>"

    for index, page_id in enumerate(page_object_ids):
        content_id = content_object_ids[index]
        objects[page_id - 1] = f"<< /Type /Page /Parent 2 0 R /MediaBox [0 0 595 842] /Resources << /Font << /F1 3 0 R >> >> /Contents {content_id} 0 R >>"

    pdf = "%PDF-1.4\n"
    offsets = [0]
    for object_id, body in enumerate(objects, start=1):
        offsets.append(len(pdf.encode("latin-1")))
        pdf += f"{object_id} 0 obj\n{body}\nendobj\n"

    xref_start = len(pdf.encode("latin-1"))
    pdf += f"xref\n0 {len(objects) + 1}\n0000000000 65535 f \n"
    for offset in offsets[1:]:
        pdf += f"{offset:010d} 00000 n \n"
    pdf += f"trailer\n<< /Size {len(objects) + 1} /Root 1 0 R >>\nstartxref\n{xref_start}\n%%EOF"

    return pdf.encode("latin-1", "replace")

@app.route("/destination-analytics", methods=["POST"])
def destination_analytics():
    data = request.get_json(silent=True) or {}
    destination = (data.get("destination") or "").strip()

    if not destination:
        return jsonify({"error": "Please enter a destination."}), 400

    prompt = f"""
    Create modern travel analytics for this destination: {destination}

    Return this exact JSON shape:
    {{
      "destination": "clean destination name",
      "summary": "2 sentence overview",
      "quick_stats": [
        {{"label": "Best For", "value": "short value"}},
        {{"label": "Trip Length", "value": "short value"}},
        {{"label": "Daily Budget", "value": "short value"}},
        {{"label": "Travel Style", "value": "short value"}}
      ],
      "packing_tips": [
        {{"title": "short title", "detail": "specific practical tip"}}
      ],
      "best_time_to_visit": [
        {{"season": "month range or season", "reason": "why it works"}}
      ],
      "safety_advice": [
        {{"title": "short title", "detail": "specific safety advice"}}
      ],
      "local_food_recommendations": [
        {{"dish": "food name", "why": "why to try it"}}
      ],
      "budget_guide": [
        {{"tier": "Budget", "daily_cost": "estimated daily range", "notes": "what this includes"}},
        {{"tier": "Comfort", "daily_cost": "estimated daily range", "notes": "what this includes"}},
        {{"tier": "Luxury", "daily_cost": "estimated daily range", "notes": "what this includes"}}
      ]
    }}

    Use 3 to 5 items for each list. If the destination is ambiguous, choose the most likely travel destination and mention the interpreted place in destination.
    """

    try:
        analytics = get_ai_json(prompt)
        analytics["source"] = "groq"
        return jsonify(analytics)
    except Exception as error:
        return jsonify(fallback_destination_analytics(destination, str(error)))

@app.route("/download-analytics-pdf", methods=["POST"])
def download_analytics_pdf():
    data = request.get_json(silent=True) or {}

    if not data.get("destination"):
        return jsonify({"error": "Generate analytics before downloading a PDF."}), 400

    pdf_bytes = analytics_to_pdf_bytes(data)
    filename = "".join(character if character.isalnum() else "-" for character in data.get("destination", "destination").lower()).strip("-")

    return Response(
        pdf_bytes,
        mimetype="application/pdf",
        headers={
            "Content-Disposition": f"attachment; filename={filename or 'destination'}-travel-analytics.pdf"
        }
    )

@app.route("/destination-inspiration", methods=["GET"])
def destination_inspiration():
    prompt = """
    Create fresh travel inspiration for a modern destination exploration page.

    Return this exact JSON shape:
    {
      "destination_cards": [
        {"name": "destination", "region": "country or region", "hook": "one vivid sentence", "best_for": "2-4 words"}
      ],
      "categories": [
        {"name": "category name", "description": "short useful description"}
      ],
      "trending_places": [
        {"name": "place", "why_trending": "short reason", "ideal_trip": "short trip style"}
      ]
    }

    Use 6 destination_cards, 6 categories, and 5 trending_places. Include a balanced global mix.
    """

    try:
        return jsonify(get_ai_json(prompt))
    except Exception:
        return jsonify({
            "destination_cards": [
                {"name": "Kyoto", "region": "Japan", "hook": "Temple lanes, tea houses, and peaceful gardens with a cinematic old-world feel.", "best_for": "Culture"},
                {"name": "Banff", "region": "Canada", "hook": "Blue lakes, alpine roads, and mountain days built for fresh-air explorers.", "best_for": "Nature"},
                {"name": "Lisbon", "region": "Portugal", "hook": "Sunny viewpoints, tiled streets, and seafood dinners that feel effortless.", "best_for": "City Break"},
                {"name": "Zanzibar", "region": "Tanzania", "hook": "Spice markets, reef-blue beaches, and Swahili coast history in one trip.", "best_for": "Beaches"},
                {"name": "Queenstown", "region": "New Zealand", "hook": "Lakefront calm with adventure sports waiting around every corner.", "best_for": "Adventure"},
                {"name": "Jaipur", "region": "India", "hook": "Royal palaces, bazaars, and desert colors made for slow discovery.", "best_for": "Heritage"}
            ],
            "categories": [
                {"name": "Beach Escapes", "description": "Warm coastlines, island stays, and slower days by the water."},
                {"name": "Mountain Retreats", "description": "Cool weather, scenic hikes, and cabins with wide-open views."},
                {"name": "Food Capitals", "description": "Destinations where the best memories start with a local plate."},
                {"name": "Cultural Cities", "description": "Museums, heritage streets, festivals, and layered local stories."},
                {"name": "Budget Gems", "description": "Places where great stays, food, and transit stay wallet-friendly."},
                {"name": "Adventure Hubs", "description": "Routes for trekking, rafting, diving, skiing, and active travel."}
            ],
            "trending_places": [
                {"name": "Seoul", "why_trending": "Design hotels, cafe culture, beauty shopping, and music-driven neighborhoods.", "ideal_trip": "Urban culture"},
                {"name": "AlUla", "why_trending": "Desert landscapes and ancient rock-cut heritage are drawing curious travelers.", "ideal_trip": "History escape"},
                {"name": "Tbilisi", "why_trending": "Food, wine, architecture, and mountain access make it great value.", "ideal_trip": "Budget discovery"},
                {"name": "Da Nang", "why_trending": "Beach life, cafes, and easy links to Hoi An and Hue.", "ideal_trip": "Relaxed coast"},
                {"name": "Madeira", "why_trending": "Cliff hikes, ocean views, and year-round mild weather.", "ideal_trip": "Nature week"}
            ]
        })
# Database (Neon)
DATABASE_URL = os.getenv("DATABASE_URL") or os.environ.get("DATABASE_URL")

def ensure_schema(conn):
    with conn.cursor() as cur:
        cur.execute("""
            CREATE TABLE IF NOT EXISTS users (
                id SERIAL PRIMARY KEY,
                name TEXT NOT NULL,
                email TEXT UNIQUE NOT NULL,
                last_login TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
                created_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP
            );
        """)
        cur.execute("""
            CREATE TABLE IF NOT EXISTS user_trips (
                id SERIAL PRIMARY KEY,
                user_id INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
                destination TEXT NOT NULL,
                created_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP
            );
        """)
        conn.commit()

def get_db_connection():
    if psycopg2 is None:
        raise RuntimeError("psycopg2 is not installed. Run: pip install psycopg2-binary")

    # 2. Connect to your Neon database
    if not DATABASE_URL:
        raise RuntimeError("DATABASE_URL is not configured in .env")

    # Keep requests snappy during local dev if Neon is unreachable.
    conn = psycopg2.connect(
        DATABASE_URL,
        connect_timeout=3,
        options="-c statement_timeout=3000",
    )
    return conn


@app.route("/health", methods=["GET"])
def health():
    try:
        conn = get_db_connection()
        try:
            with conn.cursor() as cur:
                cur.execute("SELECT 1;")
                cur.fetchone()
            return jsonify({"status": "ok"})
        finally:
            conn.close()
    except Exception as error:
        return jsonify({"status": "error", "error": str(error)}), 500


@app.route('/submit-trip', methods=['POST'])
def submit_trip():
    data = request.get_json(silent=True) or {}
    
    email = (data.get("email") or "").strip()
    name = (data.get("name") or "").strip()
    city = (data.get("city") or "Unknown").strip()   # capture city from frontend

    if not email or not name:
        return jsonify({"status": "error", "message": "Missing required data"}), 400

    try:
        saved = save_user_and_trip(name, email, city)
        return jsonify({"status": "success", "message": f"Saved trip for {email}", "user_id": saved["user_id"]})
    except Exception as error:
        return jsonify({"status": "error", "message": str(error)}), 500



def save_user_and_trip(name, email, city="Unknown"):
    conn = get_db_connection()
    try:
        ensure_schema(conn)
        with conn.cursor() as cur:
            cur.execute("""
                INSERT INTO users (name, email, last_login)
                VALUES (%s, %s, CURRENT_TIMESTAMP)
                ON CONFLICT (email)
                DO UPDATE SET last_login = CURRENT_TIMESTAMP, name = EXCLUDED.name
                RETURNING id;
            """, (name, email))

            row = cur.fetchone()
            if not row:
                raise RuntimeError("Failed to create/update user.")
            user_id = row[0]

            cur.execute("""
                INSERT INTO user_trips (user_id, destination)
                VALUES (%s, %s);
            """, (user_id, city or "Unknown"))

        conn.commit()
        return {"user_id": user_id}
    finally:
        conn.close()



if __name__ == "__main__":
    port = int(os.environ.get("PORT", "5000"))
    app.run(host="0.0.0.0", port=port, debug=False)
