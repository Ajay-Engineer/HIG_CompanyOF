from flask import Flask, request, jsonify
from flask_cors import CORS
import json
import re
import google.generativeai as genai
from serpapi.google_search import GoogleSearch

app = Flask(__name__)
CORS(app)

# Replace with your actual API keys
GEMINI_API_KEY = "AIzaSyDbLI6N8BcfYwN30uamRjKa2tQ1E525jOQ"                          # API key for Gemini
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
    company_name = data.get("company_name", "")
    if not company_name:
        return jsonify({"error": "No company name provided."}), 400

    gemini_output = get_company_info_from_gemini(company_name)

    if gemini_output and is_summary_trustworthy(gemini_output):
        parsed = extract_json_from_text(gemini_output)
        if parsed:
            return jsonify({"source": "Gemini", "data": parsed})

    search_results = search_google(company_name)
    summarized_output = summarize_with_gemini_from_search(search_results, company_name)
    parsed = extract_json_from_text(summarized_output)
    if parsed:
        return jsonify({"source": "Search + Gemini", "data": parsed})

    return jsonify({"error": "Failed to retrieve valid information."}), 500

if __name__ == "__main__":
    app.run(debug=True)
