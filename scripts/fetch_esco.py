import urllib.request
import csv
import io
import json
import os
import re

URL = "https://raw.githubusercontent.com/MaudGrol/Data_driven_skills_taxonomy/master/occupations_en.csv"
OUTPUT_FILE = os.path.join(os.path.dirname(__file__), "esco_taxonomy.json")

def main():
    print(f"Downloading ESCO Occupations from {URL}...")
    try:
        req = urllib.request.urlopen(URL)
        csv_content = req.read().decode('utf-8')
    except Exception as e:
        print(f"Error downloading data: {e}")
        return

    print("Successfully downloaded. Parsing CSV...")
    f = io.StringIO(csv_content)
    reader = csv.DictReader(f)
    
    result = {}
    row_count = 0
    
    for row in reader:
        row_count += 1
        isco = row.get("iscoGroup", "").strip()
        pref_label = row.get("preferredLabel", "").strip()
        alt_labels_str = row.get("altLabels", "").strip()
        
        # Validate 4-digit ISCO-08 code
        if not isco or len(isco) != 4 or not isco.isdigit():
            continue
            
        # Standardize labels and map to ISCO code
        if pref_label:
            result[pref_label.lower().strip()] = isco
            
        if alt_labels_str:
            # Alt labels are separated by newlines within the quoted cell
            labels = [l.strip() for l in re.split(r'[\n\r]+', alt_labels_str) if l.strip()]
            for label in labels:
                result[label.lower().strip()] = isco
                
    print(f"Processed {row_count} rows from CSV.")
    print(f"Extracted {len(result)} unique titles/aliases mapped to ISCO codes.")
    
    with open(OUTPUT_FILE, 'w', encoding='utf-8') as f_out:
        json.dump(result, f_out, indent=4)
        
    print(f"Saved to {OUTPUT_FILE}")

if __name__ == "__main__":
    main()
