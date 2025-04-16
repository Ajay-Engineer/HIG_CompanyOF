from flask import Flask, request, jsonify
from flask_cors import CORS
import json
import re
import google.generativeai as genai
from serpapi.google_search import GoogleSearch
from mongoengine import Document, StringField, IntField, DateTimeField, ListField, EmbeddedDocumentField
from mongoengine import connect



# Corrected URI with percent-encoded password
uri = "mongodb+srv://aiautomationhig:x6MJpyruWEaiUU3R@companysearchfinder.tw2yfrm.mongodb.net/?retryWrites=true&w=majority&appName=CompanySearchFinder"



try:
    connect('company_search_finder', host=uri)
    print("MongoDB connection successful")
except Exception as e:
    print("MongoDB connection failed:", e)


# Define schemas using MongoEngine
class User(Document):
    company_name= StringField(unique=True, required=True, max_length=200) # Company name
    founded_year = IntField() # Year the company was founded
    headquarters_location = StringField() # Location of the company's headquarters
    branch_locations = ListField(StringField()) # Locations of the company's branches
    core_business_or_main_focus = StringField() # Main focus or core business of the company
    pros_of_working_there = ListField(StringField()) # Pros of working at the company
    cons_of_working_there = ListField(StringField()) # Cons of working at the company
    company_culture_summary = StringField() # Summary of the company culture
    notable_achievements_or_awards = StringField() # Notable achievements or awards of the company
    fresher_friendly_rating_percent = IntField() # Rating for freshers (0-100)
    created_at = DateTimeField() # Timestamp of when the document was created
    
   

 




app = Flask(__name__)
CORS(app)

# Replace with your actual API keys
GEMINI_API_KEY = "AIzaSyBSh5HA6EVQnzJD_oeEAxibxO4XtgC7568"                          # API key for Gemini
SERP_API_KEY = "271f0d1ae537d6ef67f425980ff3fd4f14fb2cca064f2b2b7329266508ec8d57"   # API key for SerpAPI


genai.configure(api_key=GEMINI_API_KEY)
model = genai.GenerativeModel("gemini-1.5-pro-latest")

def search_google(query):
    search = GoogleSearch({"q": query, "api_key": SERP_API_KEY})
    results = search.get_dict()
    top_snippets = []
    for result in results.get("organic_results", [])[:5]:
        title = result.get("title")
        snippet = result.get("snippet", "")
        link = result.get("link")
        top_snippets.append(f"{title}\n{snippet}\n{link}")
    return "\n\n".join(top_snippets)

def is_summary_trustworthy(text, threshold=3):
    vague_phrases = [
        "information not publicly available", "not readily available", "unable to find",
        "not found", "specifics are unavailable", "check professional networking sites",
        "search for local business registries", "general pros for small businesses",
        "can be described generally as", "these are generalizations", 
        "should not be taken as factual", "recommended to consult company websites",
        "likely focused on", "best approach would be to", "details are limited"
    ]
    vague_count = 0
    try:
        json_data = re.search(r"\{.*\}", text, re.DOTALL).group(0)
        parsed = json.loads(json_data)
        for key, value in parsed.items():
            value = " ".join(value) if isinstance(value, list) else str(value)
            vague_count += sum(1 for phrase in vague_phrases if phrase in value.lower())
    except Exception:
        text = text.lower()
        vague_count = sum(1 for phrase in vague_phrases if phrase in text)
    return vague_count < threshold

def get_company_info_from_gemini(company_name):
    prompt = f"""
Act like a company information summarizer. Provide JSON only. Do not include explanations.
Give the following about "{company_name}":

- company_name
- founded_year
- headquarters_location
- branch_locations
- core_business_or_main_focus
- pros_of_working_there (list)
- cons_of_working_there (list)
- company_culture_summary
- notable_achievements_or_awards
- fresher_friendly_rating_percent (number between 0 and 100 that reflects how good this company is for freshers based on learning, career growth, work culture, and stability)

If you don't know, say "Information not publicly available".
"""
    try:
        response = model.generate_content(prompt)
        return response.text.strip()
    except:
        return None

def summarize_with_gemini_from_search(search_results, company_name):
    prompt = f"""
Based on the following search results, summarize detailed information about "{company_name}" in JSON format with:

- company_name
- founded_year
- headquarters_location
- branch_locations
- core_business_or_main_focus
- pros_of_working_there (based on employee reviews)
- cons_of_working_there (based on employee reviews)
- company_culture_summary
- notable_achievements_or_awards
- fresher_friendly_rating_percent (number between 0 and 100 that reflects how good this company is for freshers based on learning, career growth, work culture, and stability)

Search Results:
{search_results}
"""
    try:
        response = model.generate_content(prompt)
        return response.text.strip()
    except:
        return ""

def extract_json_from_text(text):
    try:
        match = re.search(r"\{.*\}", text, re.DOTALL)
        if match:
            return json.loads(match.group(0))
    except Exception as e:
        print("JSON extraction failed:", e)
    return None



@app.route("/company", methods=["POST"])
def company_lookup():
    data = request.get_json()
    company_name = data.get("company_name", "").strip()
    company_name=company_name.upper()

    # 🚫 No company name provided
    if not company_name:
        return jsonify({"error": "No company name provided."}), 400

    try:
        # ✅ Check if company already exists in DB
        existing_company = User.objects(company_name=company_name).first()
        if existing_company:
            company_data = {
                "company_name": existing_company.company_name,
                "founded_year": existing_company.founded_year,
                "headquarters_location": existing_company.headquarters_location,
                "branch_locations": existing_company.branch_locations,
                "core_business_or_main_focus": existing_company.core_business_or_main_focus,
                "pros_of_working_there": existing_company.pros_of_working_there,
                "cons_of_working_there": existing_company.cons_of_working_there,
                "company_culture_summary": existing_company.company_culture_summary,
                "notable_achievements_or_awards": existing_company.notable_achievements_or_awards,
                "fresher_friendly_rating_percent": existing_company.fresher_friendly_rating_percent,
            }
            return jsonify({"source": "DB", "data": company_data}), 200
    except Exception as e:
        print("MongoDB query failed:", e)

    # 🔮 Try Gemini API directly
    gemini_output = get_company_info_from_gemini(company_name)
    if gemini_output and is_summary_trustworthy(gemini_output):
        parsed = extract_json_from_text(gemini_output)
        if parsed:
            try:
    # 💡 Ensure lists are actually lists
                parsed['branch_locations'] = parsed.get('branch_locations', [])
                if isinstance(parsed['branch_locations'], str):
                    parsed['branch_locations'] = [parsed['branch_locations']]

                parsed['pros_of_working_there'] = parsed.get('pros_of_working_there', [])
                if isinstance(parsed['pros_of_working_there'], str):
                    parsed['pros_of_working_there'] = [parsed['pros_of_working_there']]

                parsed['cons_of_working_there'] = parsed.get('cons_of_working_there', [])
                if isinstance(parsed['cons_of_working_there'], str):
                    parsed['cons_of_working_there'] = [parsed['cons_of_working_there']]

                user = User(
                    company_name=parsed['company_name'].upper(),
                    founded_year=parsed['founded_year'],
                    headquarters_location=parsed['headquarters_location'],
                    branch_locations=parsed['branch_locations'],
                    core_business_or_main_focus=parsed['core_business_or_main_focus'],
                    pros_of_working_there=parsed['pros_of_working_there'],
                    cons_of_working_there=parsed['cons_of_working_there'],
                    company_culture_summary=parsed['company_culture_summary'],
                    notable_achievements_or_awards=str(parsed['notable_achievements_or_awards']),
                    fresher_friendly_rating_percent=parsed['fresher_friendly_rating_percent']
                )
                user.save()
                return jsonify({"source": "Gemini", "data": parsed}), 200
            except Exception as e:
                print("MongoDB save failed:", e)
                return jsonify({"error": "Failed to save Gemini data"}), 500


if __name__ == "__main__":
    app.run(debug=True)
