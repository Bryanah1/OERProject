import requests
import json

def refresh_otl_data():
    # official OTL JSON feed URL
    OTL_FEED_URL = "https://open.umn.edu/opentextbooks/textbooks.json"
    
    print(" Connecting to Open Textbook Library...")
    
    try:
        response = requests.get(OTL_FEED_URL, timeout=15)
        
        if response.status_code == 200:
            data = response.json()
            
            # Save it locally as 'otl_catalog.json'
            with open('otl_catalog.json', 'w') as f:
                json.dump(data, f, indent=4)
                
            print(f":) Success! Downloaded {len(data)} books to 'otl_catalog.json'.")
        else:
            print(f"X Failed to download. Status Code: {response.status_code}")
            
    except Exception as e:
        print(f"⚠️ An error occurred: {e}")

if __name__ == "__main__":
    refresh_otl_data()