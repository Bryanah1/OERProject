import json
import requests
from flask import Flask, render_template, request, jsonify
from bs4 import BeautifulSoup

app = Flask(__name__)

@app.route('/')
def index():
    return render_template('index.html')

def format_item(title, url, source_name, description="", query=""):
    #Normalizes data from any source, calculates a "relevance" score.
    score = 0
    title_lower = title.lower()
    desc_lower = description.lower()
    q_words = query.lower().split()

    # Scoring logic: +10 for each word in title, +5 for each word in description
    for word in q_words:
        if word in title_lower:
            score += 10
        if word in desc_lower:
            score += 5
            
    return {
        "title": title,
        "url": url,
        "source": source_name,
        "description": description[:150] + "..." if len(description) > 150 else description,
        "score": score
    }

def search_otl_catalog(query):
    results = []
    query_lower = query.lower()
    
    try:
        with open('otl_catalog.json', 'r') as f:
            raw_data = json.load(f)
            catalog = raw_data.get('data', [])
            
        for book in catalog:
            title = book.get('title', '')
            description = book.get('description', '')
            
            # check Title, Description, and Subject
            subject_names = [s.get('name', '').lower() for s in book.get('subjects', [])]
            
            if (query_lower in title.lower() or 
                query_lower in description.lower() or 
                any(query_lower in s for s in subject_names)):
                
                # extract best url
                book_url = book.get('url', '#') # Fallback
                formats = book.get('formats', [])
                for fmt in formats:
                    if fmt.get('type') == 'Online':
                        book_url = fmt.get('url')
                        break
                
                # score and format
                item = format_item(title, book_url, "Open Textbook Library", description, query)
                results.append(item)
                
    except Exception as e:
        print(f"OTL Local Search Error: {e}")
        
    return results

@app.route('/search', methods=['POST'])
def search():
    data = request.json
    user_input = data.get('course_code', '').upper().strip()
    all_results = []

    # first local data search
    try:
        with open('data.json', 'r') as f:
            db = json.load(f)

        book_id = db.get('MAPPINGS', {}).get(user_input)
        if book_id:
            book_data = db.get('RESOURCES', {}).get(book_id)
            if book_data:
                # current applied GGC verified resources get a huge score boost to stay on top
                res = format_item(book_data.get('title'), book_data.get('url'), "Verified GGC", "", user_input)
                res['score'] += 100 
                all_results.append(res)
    except Exception as e:
        print("Local data error:", e)

    # OERSI search next
    api_url = "https://oersi.org/api/search/oer_data/_search"
    query_payload = {
        "size": 15, # Fetch multiple to filter/rank them
        "query": {
            "multi_match": {
                "query": user_input,
                "fields": ["title^2", "description"]
            }
        }
    }
    headers = {"Content-Type": "application/json", "User-Agent": "GGC-App/1.0"}

    try:
        response = requests.post(api_url, json=query_payload, headers=headers, timeout=8)
        if response.status_code == 200:
            hits = response.json().get("hits", {}).get("hits", [])
            for item in hits:
                source = item.get("_source", {})
                res = format_item(
                    source.get("name", "No title"),
                    source.get("id", "#"),
                    "OERSI",
                    source.get("description", ""),
                    user_input
                )
                if res['score'] > 0: # Only add if it actually matches keywords
                    all_results.append(res)
    except Exception as e:
        print("OERSI API error:", e)

    # TRY merlot scraping (?)
    merlot_url = f"https://www.merlot.org/merlot/materials.htm?keywords={user_input}"
    try:
        resp = requests.get(merlot_url, timeout=8)
        
        if resp.status_code == 200:
            soup = BeautifulSoup(resp.text, 'html.parser')
            links = soup.select('a.materialTitle')
            for link_tag in links[:5]:
                title = link_tag.get_text(strip=True)
                url = link_tag.get('href')
                if url and not url.startswith("http"):
                    url = "https://www.merlot.org" + url
                
                res = format_item(title, url, "MERLOT", title, user_input)
                if res['score'] > 0:
                    all_results.append(res)
    except Exception as e:
        print("MERLOT error:", e)

    # OTL seacrh from other local database
    otl_matches = search_otl_catalog(user_input)
    all_results.extend(otl_matches)

    # Sort ALL results by score (highest first)
    all_results.sort(key=lambda x: x['score'], reverse=True)

    # Remove duplicates (by URL)
    seen_urls = set()
    unique_results = []
    for r in all_results:
        if r['url'] not in seen_urls:
            unique_results.append(r)
            seen_urls.add(r['url'])

    # Build final HTML string from sorted list
    final_html = ""
    if unique_results:
        for r in unique_results[:10]: # Show top 10 best matches
            source_label = f"<small style='color: #2c3e50; font-weight: bold;'>[{r['source']}]</small>"
            if r['source'] == "Verified GGC":
                source_label = "<span style='color: green; font-weight: bold;'>⭐ GGC VERIFIED</span>"

            final_html += f"<div>{source_label}<br>"
            final_html += f"<b>{r['title']}</b> (Relevance: {r['score']})<br>"
            if r['description'] and r['description'] != "...":
                final_html += f"<i style='font-size: 0.9em; color: #555;'>{r['description']}</i><br>"
            final_html += f"<a href='{r['url']}' target='_blank'>View Resource</a></div><hr>"
    else:
        final_html = "<p>No relevant resources found. Try a broader search (e.g., 'Chemistry' instead of a code).</p>"

    return jsonify({"results": final_html})

if __name__ == '__main__':
    app.run(debug=True)