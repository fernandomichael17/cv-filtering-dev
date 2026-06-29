import urllib.request
import json
import os

URL = "https://raw.githubusercontent.com/johnpcarty/Thesaurus-of-Job-Titles/master/synonym_job_titles_for_search.txt"
OUTPUT_FILE = os.path.join(os.path.dirname(__file__), "thesaurus_taxonomy.json")

def main():
    print(f"Downloading Thesaurus from {URL}...")
    try:
        req = urllib.request.urlopen(URL)
        raw_data = req.read().decode('utf-8')
    except Exception as e:
        print(f"Error downloading data: {e}")
        return

    result = {
        "social_media_specialist": [
            "social media specialist",
            "social media manager",
            "socmed specialist",
            "social media officer",
            "social media creator",
            "tiktok creator",
            "instagram manager",
            "social media specialist marketing"
        ],
        "content_creator": [
            "content creator",
            "digital content creator",
            "video creator",
            "youtube creator",
            "content coordinator",
            "content creator marketing"
        ],
        "prompt_engineer": [
            "prompt engineer",
            "ai prompt engineer",
            "prompt developer",
            "prompt specialist"
        ],
        "devops_engineer": [
            "devops engineer",
            "devops",
            "site reliability engineer",
            "sre",
            "platform engineer",
            "infrastructure engineer"
        ],
        "digital_marketing": [
            "digital marketing",
            "digital marketer",
            "online marketing",
            "online marketer",
            "internet marketing",
            "internet marketer",
            "performance marketing",
            "performance marketer",
            "seo specialist",
            "sem specialist",
            "growth hacker",
            "growth marketing",
            "growth marketer"
        ]
    }
    
    lines = raw_data.strip().split('\n')
    for line in lines:
        if '=>' not in line:
            continue
        
        parts = line.split('=>')
        synonyms_str = parts[0].strip()
        canonical = parts[1].strip()
        
        # Split synonyms by comma
        synonyms = [s.strip() for s in synonyms_str.split(',') if s.strip()]
        # Also add the canonical name itself as a synonym (just replacing _ with space)
        canonical_clean = canonical.replace('_', ' ').strip()
        if canonical_clean not in synonyms:
            synonyms.append(canonical_clean)
            
        if canonical in result:
            # Merge and de-duplicate synonyms
            merged = set(result[canonical]) | set(synonyms)
            result[canonical] = sorted(list(merged))
        else:
            result[canonical] = synonyms
    
    print(f"Successfully extracted {len(result)} canonical job title groups.")
    
    with open(OUTPUT_FILE, 'w', encoding='utf-8') as f:
        json.dump(result, f, indent=4)
        
    print(f"Saved to {OUTPUT_FILE}")

if __name__ == "__main__":
    main()
