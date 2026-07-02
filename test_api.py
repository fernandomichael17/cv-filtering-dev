import asyncio
import json
from fastapi.testclient import TestClient
from app.main import app

def test_filtering_endpoint():
    print("Mempersiapkan TestClient FastAPI...")
    client = TestClient(app)
    
    job_vacancy_id = 1
    api_key = "a93a0c99e991eef96cc4a0ac83e0036ff3732310e7187330eaca970682ea6200" # Dari .env API_KEY_FILTERING
    
    print(f"\nMengirim POST request ke /api/jobs/{job_vacancy_id}/filter ...")
    response = client.post(
        f"/api/jobs/{job_vacancy_id}/filter",
        headers={"X-API-KEY": api_key}
    )
    
    print(f"Status Code: {response.status_code}")
    if response.status_code == 200:
        data = response.json()
        print("Response berhasil diterima!")
        # Kita hanya print beberapa field utama untuk membuktikan ini FilteringResponse bukan FilterTaskResponse
        print(f"Total Candidates: {data.get('total_candidates')}")
        print(f"After Taxonomy Filter (Lolos): {data.get('after_taxonomy_filter')}")
        
        candidates = data.get("candidates", [])
        if candidates:
            print(f"\nContoh Kandidat Pertama:")
            print(json.dumps(candidates[0], indent=2))
        else:
            print("\nTidak ada kandidat yang dikembalikan.")
    else:
        print(f"Error Response: {response.text}")

if __name__ == "__main__":
    test_filtering_endpoint()
