"""Modul Kompatibilitas Bidang dan Pengecualian Lintas Rumpun taksonomi (P16)."""

import logging
from app.config import settings

logger = logging.getLogger(__name__)

# Kategori besar (BROAD_CATEGORIES) yang harus diabaikan dari cv_tags kandidat saat matching skills.
BROAD_CATEGORIES = {
    "it & software", "it", "software", "tech", "technology",
    "finance & accounting", "finance", "accounting",
    "marketing & pr", "marketing", "pr", "public relations",
    "hr & general affairs", "hr", "human resources", "general affairs",
    "engineering & manufacturing", "engineering", "manufacturing",
    "legal & compliance", "legal", "compliance",
    "operations & supply chain", "operations", "supply chain",
    "sales & business development", "sales", "business development",
    "creative & design", "creative", "design",
    "customer service", "administration", "education",
}

def get_match_type(job_code: str, exp_code: str, job_title: str = "", exp_title: str = "") -> str:
    """Menentukan tingkat kecocokan antara dua kode taksonomi ISCO berdasarkan awalan kode.

    Aturan khusus diterapkan untuk kelompok teknologi informasi (awalan "25"), serta pengecualian
    pada kelompok multi-bidang yang terlalu luas (awalan "216" dan "265") untuk menghindari
    kecocokan palsu (false positive).

    Parameter:
        job_code (str): Kode ISCO dari posisi pekerjaan lowongan.
        exp_code (str): Kode ISCO dari pengalaman kerja kandidat.
        job_title (str): Judul lowongan kerja.
        exp_title (str): Judul pengalaman kerja kandidat.

    Return:
        str: Tingkat kecocokan ("exact", "related", "loosely_related", "unrelated", atau "unknown").
    """
    if not job_code or not exp_code or job_code == "unknown" or exp_code == "unknown":
        return "unknown"
        
    # Pengetatan jabatan makro IT umum (misal: "IT", "IT Staff")
    if job_code.startswith("25") and exp_title:
        exp_lower = exp_title.strip().lower()
        job_lower = job_title.strip().lower() if job_title else ""
        
        broad_it_titles = {"it", "it staff", "staff it", "it intern", "intern it", "magang it", "it programmer assistant", "it admin"}
        is_broad_exp = exp_lower in broad_it_titles or exp_lower == "information technology"
        
        # Jika judul lowongan spesifik (bukan sekadar "IT" umum), turunkan kecocokan ke loosely_related
        if is_broad_exp and job_lower not in {"it", "information technology"}:
            return "loosely_related"
            
    if job_code == exp_code:
        return "exact"
        
    # 1. Custom Cross-Group mappings (e.g. Professional vs Technician in same domain)
    CROSS_GROUP_PAIRS = {
        # Science & Engineering
        ("2142", "3112"),  # Civil Engineer <-> Civil Infra/Technician
        ("2142", "3118"),  # Civil Engineer <-> Drafter
        ("2144", "3115"),  # Mechanical Engineer <-> Mechanical Technician
        ("2151", "3113"),  # Electrical Engineer <-> Electrical Technician
        ("2152", "3114"),  # Electronics Engineer <-> Electronics Technician
        ("2145", "3116"),  # Chemical Engineer <-> Chemical Technician
        ("2146", "3111"),  # Chemist <-> Chemical Lab Technician
        ("2161", "3118"),  # Architect <-> Drafter/Drafting Technician
        ("3112", "3118"),  # Civil Technician <-> Drafter
        
        # Property & Real Estate
        ("1323", "2142"),  # Project Manager <-> Civil Engineer
        ("1323", "3123"),  # Project Manager <-> Pengawas Proyek
        ("2142", "3123"),  # Civil Engineer <-> Pengawas Proyek
        ("3339", "1233"),  # Estate Management/Leasing <-> Leasing Manager
        ("3339", "1411"),  # Property/Estate Management <-> Building Manager
        ("3339", "4226"),  # Leasing/Estate Management <-> Tenant Relation
        ("4226", "2431"),  # Tenant Relation <-> Marketing Professional
        ("2611", "3341"),  # Legal Officer <-> Legal Admin/Secretary
        ("2263", "3119"),  # HSE Professional <-> Safety Technician
        ("2263", "3257"),  # HSE Professional <-> Environmental Inspector
        
        # ICT & Support
        ("2522", "3511"),  # Systems Admin <-> CS/IT Support
        ("2522", "3512"),  # Systems Admin <-> IT Support
        ("2523", "3513"),  # Network Professional <-> Network Technician
        ("2513", "3514"),  # Web Developer <-> Web Technician
        ("2519", "2522"),  # DevOps/Cloud/QA <-> Systems Administrator
        ("2519", "2523"),  # DevOps/Cloud/QA <-> Network Administrator
        ("2519", "3512"),  # DevOps/Cloud/QA <-> IT Support (Career Transition)
        ("2512", "3512"),  # Software Developer <-> IT Support (Career Transition)
        ("2512", "2522"),  # Software Developer <-> Systems Administrator
        ("2512", "2523"),  # Software Developer <-> Network Administrator
        ("2529", "2523"),  # Security Specialist <-> Network Administrator
        ("2529", "2522"),  # Security Specialist <-> Systems Administrator
        ("2529", "3512"),  # Security Specialist <-> IT Support
        ("2512", "2120"),  # Software Developer/ML Engineer <-> Data Scientist/Statistician
        ("2511", "2120"),  # Systems Analyst <-> Data Scientist/Statistician
        
        # Accounting & Finance
        ("2411", "4311"),  # Accountant <-> Bookkeeper
        ("2411", "4312"),  # Accountant <-> Statistical/Finance Clerk
        ("2411", "5230"),  # Accountant <-> Cashier/Teller
        ("2411", "3313"),  # Accountant <-> Accounting Associate
        ("2413", "3312"),  # Financial Analyst <-> Credit/Loans Officer
        
        # Clerical & Admin
        ("3343", "4110"),  # Secretary <-> General Office Clerk/Admin
        ("3343", "4226"),  # Secretary <-> Receptionist
        
        # Drafting & Design
        ("2166", "3435"),  # Graphic Designer <-> Design/Artistic Technician
        
        # Supply Chain & Logistics
        ("1324", "4321"),  # Supply/Distribution Manager <-> Stock Clerk
        ("1324", "4323"),  # Supply/Distribution Manager <-> Transport Clerk
        ("3323", "4321"),  # Purchasing Officer <-> Stock Clerk
        ("3331", "4323"),  # Freight Forwarder <-> Transport Clerk
        
        # Hospitality & F&B
        ("1411", "4224"),  # Hotel Manager <-> Hotel Receptionist
        ("1412", "5120"),  # Restaurant Manager <-> Cooks
        ("3434", "5120"),  # Chef <-> Cook
        ("5131", "5132"),  # Waiter <-> Bartender
        
        # HR & Training
        ("2423", "4416"),  # HR Professional <-> Personnel Clerk
        ("2424", "2320"),  # Training Professional <-> Vocational Teacher
        
        # Health
        ("2221", "3221"),  # Nursing Professional <-> Nursing Associate
        ("2222", "3222"),  # Midwifery Professional <-> Midwifery Associate
        ("2262", "3213"),  # Pharmacist <-> Pharmacy Technician
        ("2261", "3251"),  # Dentist <-> Dental Assistant
        
        # Sales & Marketing
        ("2431", "3322"),  # Marketing Professional <-> Sales Representative
        ("1221", "2431"),  # Sales/Marketing Manager <-> Marketing Professional
        ("2431", "2642"),  # Marketing Professional <-> Journalists (Content Creator)
        ("2431", "2641"),  # Marketing Professional <-> Authors/Writers (Copywriter)
        ("1222", "2431"),  # Advertising/PR Manager <-> Marketing Professional
        ("1222", "2432"),  # Advertising/PR Manager <-> PR Professional
        ("1222", "2642"),  # Advertising/PR Manager <-> Journalists (Content Creator)
        ("1221", "2432"),  # Sales/Marketing Manager <-> PR Professional
        ("1221", "2642"),  # Sales/Marketing Manager <-> Journalists (Content Creator)
    }
    
    if (job_code, exp_code) in CROSS_GROUP_PAIRS or (exp_code, job_code) in CROSS_GROUP_PAIRS:
        return "related"
        
    # 2. 3-digit match (Related Rumpun)
    # Pengecualian khusus untuk sub-major groups yang terlalu luas:
    # - 216 (Architects/Designers): UI/UX 2166 vs GIS 2165 vs Arsitek 2161 sangat berbeda
    # - 265 (Creative/Performing Artists): terlalu beragam
    # - 252 (Database & Network Professionals): Data Eng 2521 vs SysAdmin 2522 vs Network 2523
    #   sangat berbeda di dunia kerja modern meskipun ISCO-08 mengelompokkan mereka
    if job_code[:3] == exp_code[:3]:
        if job_code.startswith(("216", "265", "252")) or exp_code.startswith(("216", "265", "252")):
            return "loosely_related"
        return "related"
        
    # 3. Strict rule for IT / ICT Group (starts with "25")
    # If both are under ICT, but do not share the same 3-digit prefix (e.g. software 251 vs database 252),
    # they are at best loosely_related to prevent auto-passing cross-discipline roles.
    if job_code.startswith("25") and exp_code.startswith("25"):
        return "loosely_related"

    # 4. 2-digit match for general groups (excluding restricted Sub-majors 21 and 26)
    # as 21 and 26 are too broad and cause false positives (e.g. Civil Engineer matching Data Scientist)
    if not (job_code.startswith("21") and exp_code.startswith("21")) and not (job_code.startswith("26") and exp_code.startswith("26")):
        if job_code[:2] == exp_code[:2]:
            return "loosely_related"

    # 5. Cluster Fallback (safety net for related cross-disciplinary domains)
    # PENTING: Cluster harus spesifik. Jangan menggabungkan sub-disiplin yang berbeda jauh
    # dalam satu cluster (contoh: Network Technician vs Data Engineer).
    TAXONOMY_CLUSTERS = [
        # Cluster A: Software Development & Data (Developer, Analyst, Data Engineer, QA)
        # TIDAK termasuk Network/Infrastructure (2522, 2523, 3513, 3511)
        {"2511", "2512", "2513", "2514", "2519", "2521", "2529", "2120"},
        # Cluster B: ICT Infrastructure & Network (SysAdmin, Network Prof, ICT Support, Network Tech)
        # TIDAK termasuk Software Development atau Data Engineering
        {"2522", "2523", "3511", "3513", "2152", "2153"},
        # Engineering (Mechanical, Civil, Chemical, Electrical, Drafters, Engineering Technicians)
        {"214", "2151", "311"},
        # Business, Finance & Administration (Accountants, HR, Clerks, Secretaries, Admins)
        {"241", "242", "331", "332", "333", "334", "41", "42", "43"},
    ]
    
    def get_cluster_index(code: str) -> int | None:
        for idx, cluster in enumerate(TAXONOMY_CLUSTERS):
            for prefix in cluster:
                if code.startswith(prefix):
                    return idx
        return None

    job_cluster = get_cluster_index(job_code)
    exp_cluster = get_cluster_index(exp_code)
    if job_cluster is not None and job_cluster == exp_cluster:
        return "loosely_related"

    return "unrelated"




def _is_bypass_allowed(job_title: str) -> bool:
    """
    Menentukan apakah bypass lintas bidang diperbolehkan untuk posisi pekerjaan tertentu.
    Bypass diperbolehkan untuk posisi umum/entry-level, namun dimatikan untuk posisi spesialis/teknis.

    Parameter:
        job_title (str): Judul posisi pekerjaan.

    Return:
        bool: True jika bypass diperbolehkan, False jika dilarang.
    """
    general_roles = ["sales", "marketing", "admin", "customer service", "staf", "staff", "spg", "spb", "management trainee", "mt", "trainee"]
    managerial_roles = ["manager", "head", "director", "supervisor", "lead"]
    specialist_keywords = ["specialist", "ads", "seo", "performance", "developer", "engineer", "analyst"]

    job_title_lower = job_title.lower()
    is_general = any(g in job_title_lower for g in general_roles)
    is_manager = any(m in job_title_lower for m in managerial_roles)
    is_specialist = any(s in job_title_lower for s in specialist_keywords)

    return is_general and not is_manager and not is_specialist




def _are_fields_compatible(job_field: str | None, exp_field: str | None) -> bool:
    """
    Memeriksa apakah bidang pekerjaan (job field) dari lowongan dan pengalaman kerja kompatibel.
    Menghindari kecocokan palsu (false positive) lintas bidang yang tidak memiliki irisan fungsional.

    Parameter:
        job_field (str | None): Bidang pekerjaan dari lowongan (misalnya "IT & Software").
        exp_field (str | None): Bidang pekerjaan dari riwayat CV (misalnya "Engineering & Manufacturing").

    Return:
        bool: True jika kompatibel atau salah satunya kosong, False jika bertolak belakang.
    """
    if not job_field or not exp_field:
        return True

    jf = job_field.strip().lower()
    ef = exp_field.strip().lower()

    if jf == ef:
        return True

    # 1. Penanganan khusus jika salah satu merupakan substring dari yang lain
    # (e.g., "it" dengan "it & software", atau "admin" dengan "administration")
    if jf in ef or ef in jf:
        return True

    # 2. Penanganan khusus untuk rumpun Teknologi Informasi dan Desain (IT / Software / Tech / UI / UX / Design)
    # untuk mengantisipasi tag buatan di unit test atau ekstraksi bidang kreatif (seperti "ui/ux designer")
    tech_keywords = {
        "it", "software", "tech", "python", "golang", "php", "laravel", "node", 
        "java", "react", "vue", "angular", "flutter", "swift", "mobile", "app", 
        "devops", "cloud", "platform", "database", "data", "qa", "tester", "programming", "developer",
        "ui", "ux", "design", "designer"
    }
    is_jf_tech = any(kw in jf for kw in tech_keywords)
    is_ef_tech = any(kw in ef for kw in tech_keywords)
    if is_jf_tech and is_ef_tech:
        return True

    # 3. Pemetaan kelompok bidang yang memiliki irisan fungsional
    compat = {
        "it & software": {"it & software", "creative & design", "education", "it", "software", "tech"},
        "finance & accounting": {"finance & accounting", "administration", "operations & supply chain", "finance", "accounting"},
        "engineering & manufacturing": {"engineering & manufacturing", "operations & supply chain", "engineering", "manufacturing"},
        "administration": {"administration", "finance & accounting", "hr & general affairs", "customer service"},
        "hr & general affairs": {"hr & general affairs", "administration", "hr", "general affairs"},
        "marketing & pr": {"marketing & pr", "sales & business development", "creative & design", "marketing", "pr"},
        "sales & business development": {"sales & business development", "marketing & pr", "sales"},
        "operations & supply chain": {"operations & supply chain", "engineering & manufacturing", "finance & accounting"},
        "customer service": {"customer service", "administration"},
        "creative & design": {"creative & design", "marketing & pr", "it & software", "design"},
    }

    # Cek apakah ada irisan kecocokan di dalam pemetaan
    for key, allowed in compat.items():
        if key in jf:
            if any(a in ef for a in allowed):
                return True
    return False



