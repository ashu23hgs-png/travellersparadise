import json
import os
import re
import logging
from flask import Flask, Response, request, jsonify, send_from_directory
from flask_cors import CORS
from openai import OpenAI
from dotenv import load_dotenv
try:
    import psycopg2
except ImportError:
    psycopg2 = None

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


app = Flask(__name__)
# Local dev CORS: Live Server (5500) -> Flask (5000). Production via env.
_default_cors_origins = [
    "http://127.0.0.1:5500",
    "http://localhost:5500",
    "http://127.0.0.1:5000",
    "http://localhost:5000",
    "https://travellers-paradise.onrender.com",
]
_extra_cors = os.getenv("CORS_ORIGINS", "")
CORS_ORIGINS = _default_cors_origins + [
    origin.strip()
    for origin in _extra_cors.split(",")
    if origin.strip()
]
CORS(
    app,
    resources={
        r"/*": {
            "origins": CORS_ORIGINS,
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
@app.route("/my-trips.html")
def trips():
    return send_from_directory(".", "my-trips.html")
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
    
@app.route('/robots.txt')
def robots_txt():
    return send_from_directory(".", "robots.txt")
@app.route('/sitemap.xml')
def sitemap():
    return send_from_directory(".", "sitemap.xml")
@app.route('/BingSiteAuth.xml')
def BingSiteAuth():
    return send_from_directory(".", "BingSiteAuth.xml")
@app.route('/googlefe3b2a6c27cef4e0.html')
def google_verification():
    return send_from_directory(".", "googlefe3b2a6c27cef4e0.html")
@app.route('/meteor-shower-calendar-india-2026.html')
def meteor_shower_calendar():
    return send_from_directory(".", "meteor-shower-calendar-india-2026.html")
@app.route('/things-to-do-in-bangalore-at-night.html')
def things_to_do_in_bangalore():
    return send_from_directory(".", "things-to-do-in-bangalore-at-night.html")
@app.route('/best-stargazing-places-near-bangalore-2026.html')
def best_stargazing_places_near_bangalore():
    return send_from_directory(".", "best-stargazing-places-near-bangalore-2026.html")
GENERIC_PLACE_PATTERNS = [
    re.compile(
        r"\b(old town walk|public square|street food lane|city center|top attraction|"
        r"dinner district|museum exterior|riverside walk|hidden alleys|sunset stroll|"
        r"easy evening|souvenir street|public garden|shopping street|night market|"
        r"cafe stop|local market|cultural spot|evening walk|live music area|"
        r"relaxed night out|premium landmark|curated city tour|rooftop dinner|"
        r"designer district|cocktail lounge|gourmet tasting|elegant night walk)\b",
        re.IGNORECASE,
    ),
    re.compile(
        r"^(?P<city>[\w\s'.-]+)\s+"
        r"(old town|public square|street food|city center|top attraction|viewpoint|"
        r"shopping street|night market|museum|local market|hidden alleys|"
        r"souvenir street|public garden|cultural spot|famous landmark|dinner district)\b",
        re.IGNORECASE,
    ),
]

SLOT_ORDER = ["Morning", "Afternoon", "Evening"]


def get_travel_level(budget):
    try:
        amount = float(budget or 0)
    except (TypeError, ValueError):
        amount = 0

    if amount > 2000:
        return "luxury"
    if amount > 1000:
        return "standard"
    return "budget"


def extract_place_name(slot):
    if not isinstance(slot, dict):
        return ""

    for key in ("place", "venue", "location", "name", "destination", "spot"):
        value = slot.get(key)
        if value:
            return str(value).strip()

    return ""


def extract_activity_text(slot):
    if not isinstance(slot, dict):
        return ""

    for key in ("activity", "description", "plan", "details", "experience"):
        value = slot.get(key)
        if value:
            return str(value).strip()

    return ""


def place_label_from_slot(slot):
    if isinstance(slot, str):
        return slot.strip()

    return format_slot_label(extract_place_name(slot), extract_activity_text(slot))


def is_generic_place_name(place, city=""):
    """Only flag obvious template placeholders, not real short venue names."""
    text = str(place or "").strip()
    if not text or len(text) < 3:
        return True

    lowered = text.lower()
    for pattern in GENERIC_PLACE_PATTERNS:
        if pattern.search(lowered):
            return True

    city_token = str(city or "").strip().lower()
    if city_token and lowered == city_token:
        return True

    if city_token and lowered.startswith(city_token + " "):
        suffix = lowered[len(city_token) + 1 :].strip()
        generic_suffixes = (
            "old town",
            "old town walk",
            "public square",
            "street food lane",
            "city center",
            "top attraction",
            "local market",
            "shopping street",
            "night market",
            "museum exterior",
            "riverside walk",
        )
        if suffix in generic_suffixes:
            return True

    return False


def place_part_from_label(label):
    text = str(label or "").strip()
    for separator in ("—", "–", "-", "|"):
        if separator in text:
            return text.split(separator, 1)[0].strip()
    return text


def format_slot_label(place, activity):
    place = str(place or "").strip()
    activity = str(activity or "").strip()
    if place and activity:
        return f"{place} — {activity}"
    return place or activity


def normalize_itinerary_payload(payload, expected_days):
    raw_days = payload.get("days") or payload.get("itinerary") or []
    normalized = []

    for day_entry in raw_days[:expected_days]:
        labels = []

        if isinstance(day_entry, list):
            labels = [place_label_from_slot(item) for item in day_entry]
            labels = [label for label in labels if label]
        elif isinstance(day_entry, dict):
            slots = day_entry.get("slots") or day_entry.get("activities") or day_entry.get("plan")
            if isinstance(slots, list):
                for slot_name in SLOT_ORDER:
                    slot = next(
                        (
                            item
                            for item in slots
                            if str(item.get("time", item.get("period", ""))).strip().lower()
                            == slot_name.lower()
                        ),
                        None,
                    )
                    if not slot and len(slots) > len(labels):
                        slot = slots[len(labels)]

                    label = place_label_from_slot(slot)
                    if label:
                        labels.append(label)

        if labels:
            normalized.append(labels)

    return normalized


def count_generic_slots(days, city):
    generic_count = 0
    total = 0

    for day in days:
        for label in day:
            total += 1
            if is_generic_place_name(place_part_from_label(label), city):
                generic_count += 1

    return generic_count, total


def build_itinerary_prompt(city, budget, days, level, strict=False):
    strict_note = (
        "Your previous answer used generic placeholders. "
        "Use ONLY real, searchable venue names that exist in or near this destination."
        if strict
        else ""
    )

    return f"""
Create a detailed travel itinerary for Traveller's Paradise.

Destination: {city}
Total budget: ${budget} USD (entire trip)
Duration: {days} day(s)
Travel style: {level}

Rules:
- Every slot must name a REAL place (landmark, park, waterfall, temple, market, cafe, restaurant, plantation, viewpoint, museum, theme park, etc.).
- Use the official or commonly known name (examples for Bengaluru: Lalbagh Botanical Garden, Vidhana Soudha, Wonderla Bengaluru, Cubbon Park, Commercial Street).
- Forbidden generic labels: "old town walk", "public square", "street food lane", "city center", "top attraction", or "{city.lower()} + generic noun".
- Match the {level} budget (hostels/street food vs boutique hotels/fine dining).
- Spread famous sights across days; avoid repeating the same place.
- Keep each activity to one short sentence.
{strict_note}

Return this exact JSON shape:
{{
  "destination": "clean destination name with region/country if helpful",
  "days": [
    {{
      "day": 1,
      "slots": [
        {{"time": "Morning", "place": "Real Place Name", "activity": "what to do"}},
        {{"time": "Afternoon", "place": "Real Place Name", "activity": "what to do"}},
        {{"time": "Evening", "place": "Real Place Name", "activity": "what to do"}}
      ]
    }}
  ]
}}

Provide exactly {days} day object(s), each with exactly 3 slots (Morning, Afternoon, Evening).
"""


def request_itinerary_json(city, budget, days, level, strict=False):
    prompt = build_itinerary_prompt(city, budget, days, level, strict=strict)
    ai_client = create_ai_client()

    response = ai_client.chat.completions.create(
        model=GROQ_MODEL,
        response_format={"type": "json_object"},
        messages=[
            {
                "role": "system",
                "content": (
                    "You are an expert travel planner for Traveller's Paradise. "
                    "Return only valid JSON. Use real venues that travelers can find on Google Maps. "
                    "Never invent generic place names."
                ),
            },
            {"role": "user", "content": prompt},
        ],
        temperature=0.35,
    )

    content = response.choices[0].message.content
    return json.loads(content)


@app.route("/generate", methods=["POST"])
def generate_trip():
    data = request.get_json(silent=True) or {}

    city = (data.get("city") or "").strip()
    budget = data.get("budget")
    days_raw = data.get("days")

    if not city:
        return jsonify({"error": "Please provide a destination city."}), 400

    try:
        days = max(1, min(14, int(days_raw)))
    except (TypeError, ValueError):
        days = 3

    level = get_travel_level(budget)

    try:
        create_ai_client()
    except RuntimeError as error:
        return jsonify({"error": str(error)}), 500

    try:
        normalized_days = []
        payload = {}
        warning = None

        for attempt, strict in enumerate((False, True, True)):
            payload = request_itinerary_json(city, budget, days, level, strict=strict)
            normalized_days = normalize_itinerary_payload(payload, days)
            generic_count, total = count_generic_slots(normalized_days, city)
            generic_ratio = generic_count / total if total else 0

            if len(normalized_days) < days:
                continue

            if generic_ratio <= 0.34:
                break

            if attempt == 2:
                warning = (
                    "Some stops may be approximate — tap Regenerate for another AI pass."
                )
                break

        if len(normalized_days) < days:
            return jsonify(
                {
                    "error": "The AI returned an incomplete itinerary. Please tap Regenerate to try again.",
                }
            ), 502

        destination = (payload.get("destination") or city).strip()
        response_body = {
            "destination": destination,
            "level": level,
            "days": normalized_days,
        }
        if warning:
            response_body["warning"] = warning

        return jsonify(response_body)
    except json.JSONDecodeError:
        return jsonify({"error": "The AI returned an invalid response. Please try again."}), 502
    except Exception as error:
        return jsonify({"error": f"Itinerary generation failed: {error}"}), 500

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

    if not DATABASE_URL:
        raise RuntimeError("DATABASE_URL is not configured. Add it to your environment variables or .env file")

    try:
        conn = psycopg2.connect(
            DATABASE_URL,
            connect_timeout=5,
            options="-c statement_timeout=5000",
        )
        return conn
    except psycopg2.OperationalError as e:
        raise RuntimeError(f"Failed to connect to database: {str(e)}")


@app.route("/health", methods=["GET"])
def health():
    try:
        conn = get_db_connection()
        try:
            with conn.cursor() as cur:
                cur.execute("SELECT 1;")
                cur.fetchone()
            logger.info("Database health check passed")
            return jsonify({"status": "ok", "message": "Database connection successful"})
        finally:
            conn.close()
    except Exception as error:
        error_msg = str(error)
        logger.error(f"Health check failed: {error_msg}")
        return jsonify({"status": "error", "error": error_msg}), 500


@app.route('/submit-trip', methods=['POST'])
def submit_trip():
    data = request.get_json(silent=True) or {}

    email = (data.get("email") or "").strip()
    name = (data.get("name") or "").strip()
    city = (data.get("city") or "Unknown").strip()

    logger.info(f"Received login request: email={email}, name={name}, city={city}")

    if not email or not name:
        error_msg = "Missing required email and name"
        logger.warning(f"{error_msg}: email={email}, name={name}")
        return jsonify({"status": "error", "message": error_msg}), 400

    try:
        saved = save_user_and_trip(name, email, city)
        logger.info(f"Successfully saved user {email} to database")
        return jsonify({"status": "success", "message": f"Saved trip for {email}", "user_id": saved["user_id"]})
    except RuntimeError as error:
        error_msg = str(error)
        logger.error(f"RuntimeError saving user {email}: {error_msg}")
        return jsonify({"status": "error", "message": error_msg}), 500
    except Exception as error:
        error_msg = f"{type(error).__name__}: {str(error)}"
        logger.error(f"Unexpected error saving user {email}: {error_msg}", exc_info=True)
        return jsonify({"status": "error", "message": error_msg}), 500



def save_user_and_trip(name, email, city="Unknown"):
    conn = get_db_connection()
    try:
        ensure_schema(conn)

        with conn.cursor() as cur:
            # Insert or update user
            cur.execute("""
                INSERT INTO users (name, email, last_login)
                VALUES (%s, %s, CURRENT_TIMESTAMP)
                ON CONFLICT (email)
                DO UPDATE SET last_login = CURRENT_TIMESTAMP, name = EXCLUDED.name
                RETURNING id;
            """, (name, email))

            row = cur.fetchone()
            if not row:
                raise RuntimeError("Failed to create/update user in database.")
            user_id = row[0]

            # Insert trip record
            cur.execute("""
                INSERT INTO user_trips (user_id, destination)
                VALUES (%s, %s);
            """, (user_id, city or "Unknown"))

        conn.commit()
        return {"user_id": user_id, "email": email}
    except psycopg2.Error as db_error:
        try:
            conn.rollback()
        except:
            pass
        raise RuntimeError(f"Database error: {str(db_error)}")
    except Exception as error:
        try:
            conn.rollback()
        except:
            pass
        raise
    finally:
        conn.close()



if __name__ == "__main__":
    port = int(os.environ.get("PORT", "5000"))
    app.run(host="0.0.0.0", port=port, debug=False)
