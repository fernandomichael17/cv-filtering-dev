import os
import sys
import time
import random

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from core.filtering.hard_filter import apply_hard_filters
from core.filtering.category_filter import check_category_compatibility
from core.filtering.taxonomy_matcher import match_job_role
from core.filtering.skills_filter import apply_skills_filter
from core.filtering.scoring import calculate_candidate_score
from app.services.filtering_service import adjust_score_by_tier

# --- MOCK CLASSES ---
class MockTags:
    def __init__(self, tags):
        self.tags = tags

class MockCandidateTags:
    def __init__(self, tags):
        self.tags = tags

class MockEducation:
    def __init__(self, major, education_id=3, score="3.50", institutionname="Universitas"):
        self.education_id = education_id
        self.major = major
        self.score = score
        self.institutionname = institutionname
        self.startyear = 2016
        self.endyear = 2020

class MockExperience:
    def __init__(self, role_name, tags, companyname="PT Contoh", startyear=2020, endyear=2023):
        self.startdate = None
        self.enddate = None
        self.startyear = startyear
        self.endyear = endyear
        self.iscurrent = False
        self.jobdesk = ""
        self.joblevel = role_name
        self.companyname = companyname
        self.experience_tags = MockTags(tags)

class MockCandidateSkill:
    def __init__(self, hard_skill="", soft_skill="", language=""):
        self.hard_skill = hard_skill
        self.soft_skill = soft_skill
        self.language = language

class MockCandidate:
    def __init__(self, requireid, firstname="A", lastname="B", is_fresh_graduate=False):
        self.requireid = requireid
        self.firstname = firstname
        self.lastname = lastname
        self.gender = "Pria"
        self.dateofbirth = "1995-01-01"
        self.is_fresh_graduate = is_fresh_graduate
        self.q16_available_from = None
        self.q15_expected_income = "5000000"
        self.educations = []
        self.work_experiences = []
        self.trainings = []
        
        skills = ["Python, SQL, AWS", "Marketing, SEO", "Design, Figma", "HR, Recruitment, Excel", "Sales, Negotiation"]
        self.candidate_tags = MockCandidateTags(random.choice(skills))
        self.candidate_skills = MockCandidateSkill(hard_skill=random.choice(skills))

def generate_candidates(n: int) -> list[MockCandidate]:
    cands = []
    majors = ["Teknik Informatika", "Manajemen", "Ilmu Komunikasi", "Akuntansi"]
    for i in range(n):
        c = MockCandidate(requireid=i+1, is_fresh_graduate=(i % 4 == 0))
        c.educations.append(MockEducation(major=random.choice(majors), score=str(random.uniform(2.8, 3.9))[:4]))
        if not c.is_fresh_graduate:
            c.work_experiences.append(MockExperience(
                role_name="Staff",
                tags=c.candidate_tags.tags,
                startyear=2018 + (i % 3),
                endyear=2023
            ))
        cands.append(c)
    return cands

def run_benchmark(n_candidates: int):
    print(f"\n[{n_candidates} KANDIDAT] Menyiapkan data tiruan...")
    candidates = generate_candidates(n_candidates)
    
    job_criteria = {
        "min_education": "S1",
        "min_gpa": 3.0,
        "max_age": 35,
        "min_experience_years": 1.0,
        "max_experience_years": None,
        "required_skills": ["Python", "SQL", "Communication"],
        "job_category": "Teknologi Informasi"
    }
    parsed_job = {
        "job_category": "Teknologi Informasi",
        "job_role_category": "Software Engineer"
    }
    
    print(f"[{n_candidates} KANDIDAT] Memulai perhitungan filtering (CPU-bound)...")
    
    start_time = time.perf_counter()
    
    # 1. Bypass Hard Filters (Anggap semua kandidat jenius dan lolos tahap awal)
    passed_hard = candidates
    print(f"[*] Meloloskan {len(passed_hard)} kandidat secara otomatis dari Hard Filter untuk menguji beban maksimal (Worst-Case Scenario)...")
            
    # 2 & 3. Taxonomy Matching & Category (Sekuensial)
    taxonomy_results = {}
    for cand in passed_hard:
        cand_role = "Staff" # Dummy
        role_res = match_job_role(cand_role, parsed_job.get("job_role_category", ""), 1.0)
        taxonomy_results[cand.requireid] = role_res
        
    # 4. Skills Filter (Beroperasi pada *batch* list kandidat)
    skill_passed, skill_elim = apply_skills_filter(
        candidates=passed_hard, 
        requirements=job_criteria, 
        taxonomy_results=taxonomy_results
    )
    
    # 5. Scoring (Sekuensial untuk yang lolos)
    results = []
    for cand in skill_passed:
        cat_score = check_category_compatibility("Teknologi Informasi", parsed_job.get("job_category", ""))
        tax_res = taxonomy_results.get(cand.requireid, {})
        
        try:
            score, breakdown = calculate_candidate_score(cand, job_criteria, tax_res, "Software Engineer")
            adjusted_score = adjust_score_by_tier(score, "LAYAK")
            results.append(adjusted_score)
        except Exception as e:
            pass
        
    end_time = time.perf_counter()
    duration_sec = end_time - start_time
    
    print(f"[*] Total waktu pemrosesan {n_candidates} kandidat: {duration_sec:.4f} detik")
    print(f"[*] Rata-rata waktu per kandidat: {(duration_sec / n_candidates) * 1000:.2f} ms")
    if duration_sec > 0:
         print(f"[*] Estimasi kapasitas sistem: {int(n_candidates / duration_sec)} kandidat / detik")
    
    print(f"[*] Statistik Lolos: Hard Filter ({len(passed_hard)}/{n_candidates}), Skills Filter ({len(skill_passed)}/{len(passed_hard)}), Final Scoring ({len(results)}/{len(skill_passed)})")
    
    if duration_sec < 10.0:
        print(f"[SUCCESS] Latensi {duration_sec:.4f}s AMAN (di bawah target 10s)")
    else:
        print(f"[WARNING] Latensi {duration_sec:.4f}s melampaui target 10s!")

if __name__ == "__main__":
    print("====================================================")
    print(" BENCHMARK LATENCY MESIN FILTERING (CPU-BOUND ONLY)")
    print("====================================================")
    print("Melakukan pemanasan (*warming up*) model (initial load)...")
    _ = apply_skills_filter(generate_candidates(1), {"required_skills": ["test"]})
    
    run_benchmark(100)
    run_benchmark(500)
    run_benchmark(1000)
    run_benchmark(5000)
    print("\nBenchmark selesai.")
