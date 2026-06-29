import json
import urllib.request
import os

URL = "https://raw.githubusercontent.com/patriciomacadden/isco.json/master/en.json"
OUTPUT_FILE = os.path.join(os.path.dirname(__file__), "isco_taxonomy.json")

def extract_unit_groups(node, result):
    """
    Recursively extract all 4-digit 'unit_groups' from the ISCO hierarchy.
    """
    if isinstance(node, dict):
        if "unit_groups" in node:
            for unit in node["unit_groups"]:
                result[unit["code"]] = unit["name"]
        
        # Traverse downwards
        for key, value in node.items():
            if isinstance(value, (dict, list)):
                extract_unit_groups(value, result)
                
    elif isinstance(node, list):
        for item in node:
            extract_unit_groups(item, result)

def main():
    print(f"Downloading ISCO-08 JSON from {URL}...")
    try:
        req = urllib.request.urlopen(URL)
        raw_data = req.read().decode('utf-8')
        data = json.loads(raw_data)
    except Exception as e:
        print(f"Error downloading data: {e}")
        return

    result = {}
    extract_unit_groups(data, result)
    
    print(f"Successfully extracted {len(result)} unit groups (4-digit codes).")
    
    with open(OUTPUT_FILE, 'w', encoding='utf-8') as f:
        json.dump(result, f, indent=4)
        
    print(f"Saved to {OUTPUT_FILE}")

if __name__ == "__main__":
    main()
