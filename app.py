import os
import requests
from flask import Flask, render_template, request, jsonify
from openai import OpenAI

app = Flask(__name__)

# Initialize client (Use key here)
client = OpenAI(api_key="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")

def get_oer_data(course_query):
    """Phase II Strategy: Data Retrieval from real OER repositories"""
    # Using OER Commons API (Public Search)
    url = f"https://www.oercommons.org/api/v1/items?q={course_query}&f.search_type=textbook"
    try:
        response = requests.get(url, timeout=10)
        return response.json().get('results', [])
    except:
        return []

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/search', methods=['POST'])
def search():
    course_code = request.json.get('course_code', '').upper()
    
    # Retrieval Stage
    raw_resources = get_oer_data(course_code)
    context_text = ""
    for item in raw_resources[:5]:
        context_text += f"Title: {item.get('title')} | Link: {item.get('url')}\n"

    try:
        # UPDATED SYNTAX FOR NEW OPENAI LIBRARY
        response = client.chat.completions.create(
            model="gpt-3.5-turbo",
            messages=[
                {"role": "system", "content": "You are a precise GGC Academic AI Agent."},
                {"role": "user", "content": f"Context: {context_text}\n\nTask: Find 3 resources for {course_code}."}
            ],
            temperature=0.1
        )
        return jsonify({"results": response.choices[0].message.content})
    except Exception as e:
        print(f"Error: {e}") # This prints the REAL error to your terminal
        return jsonify({"results": "The AI Agent encountered an error. Check terminal."}), 500

if __name__ == '__main__':
    app.run(debug=True)