import json
from flask import Flask, render_template, request, jsonify

app = Flask(__name__)

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/search', methods=['POST'])
def search():
    data = request.json
    user_input = data.get('course_code', '').upper().strip()
    
    # Load local source
    try:
        with open('data.json', 'r') as f:
            local_db = json.load(f)
        
        # Search the local data
        results = local_db.get(user_input, [])
        
        if not results:
            return jsonify({"results": f"No resources found for '{user_input}'. Try 'PROGRAMMING' or 'ITEC 4700'."})

        output = f" Verified OER for {user_input}:\n\n"
        for item in results:
            output += f"{item['title']}<br><a href='{item['url']}' target='_blank' class='result-link'>Access Resource</a>\n\n"
        
        return jsonify({"results": output})
        
    except Exception as e:
        return jsonify({"results": f"System Error: {str(e)}"}), 500

if __name__ == '__main__':
    app.run(debug=True)