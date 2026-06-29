"""Skill synonyms dictionary and normalization utility.

Menyediakan dua mekanisme normalisasi:
1. SYMBOL_NORMALIZATION_MAP — menangani karakter non-alfanumerik (c++ → cpp, .net → dotnet).
2. SKILL_SYNONYMS — memetakan variasi nama ke bentuk kanonik (reactjs → react).
"""

# ── Peta Normalisasi Simbol ──────────────────────────────────────────────────
# Menangani karakter khusus yang sering hilang saat normalisasi string biasa.
# Entri diurutkan dari pola terpanjang ke terpendek untuk mencegah pencocokan parsial.
SYMBOL_NORMALIZATION_MAP = {
    # Bahasa pemrograman dengan simbol
    "c++": "cpp",
    "c#": "csharp",
    "f#": "fsharp",
    "objective-c": "objective c",
    # Framework/platform dengan titik
    ".net": "dotnet",
    ".net core": "dotnet core",
    ".net framework": "dotnet framework",
    "asp.net": "aspnet",
    "node.js": "nodejs",
    "react.js": "reactjs",
    "vue.js": "vuejs",
    "next.js": "nextjs",
    "nuxt.js": "nuxtjs",
    "express.js": "expressjs",
    "nest.js": "nestjs",
    "three.js": "threejs",
    "d3.js": "d3js",
    "ember.js": "emberjs",
    "backbone.js": "backbonejs",
    "angular.js": "angularjs",
    # Notasi umum non-IT
    "s&p": "snp",
    "r&d": "rnd",
    "f&b": "fnb",
}

SKILL_SYNONYMS = {
    "postgresql": ["postgres", "psql", "pgsql"],
    "tensorflow": ["tensorflow 2", "tf", "tensorflow2"],
    "javascript": ["js", "ecmascript", "es6"],
    "react": ["reactjs", "react.js"],
    "nodejs": ["node.js", "node"],
    "python": ["python3", "python 3"],
    "microsoft excel": ["ms excel", "excel"],
    "kubernetes": ["k8s"],
    "machine learning": ["ml", "pembelajaran mesin"],
    "data science": ["ilmuwan data madya", "ilmuwan data", "data scientist", "data science"],
    "pajak": ["taxation", "tax", "perpajakan", "tax compliance", "kepatuhan pajak"],
    "brevet pajak": ["brevet pajak a & b", "brevet pajak a", "brevet pajak b", "brevet", "brevet pajak", "brevet a", "brevet b", "brevet c"],
    "power bi": ["powerbi"],
    "adobe photoshop": ["photoshop"],
    "golang": ["go", "go lang"],
    "typescript": ["ts"],
    "mongodb": ["mongo"],
    "vuejs": ["vue.js", "vue"],
    "html": ["html5", "html 5"],
    "css": ["css3", "css 3"],
    "amazon web services": ["aws"],
    "google cloud platform": ["gcp"],
    "microsoft azure": ["azure"],
    "cpp": ["c++"],
    "csharp": ["c#"],
    "dotnet": [".net"],
    "aspnet": ["asp.net"],
    "nextjs": ["next.js"],
    "nuxtjs": ["nuxt.js"],
    "expressjs": ["express.js"],
    "nestjs": ["nest.js"],
    "fnb": ["f&b", "food and beverage", "food & beverage"],
    "first aid": ["p3k", "pertolongan pertama pada kecelakaan", "pertolongan pertama"],
    "job safety analysis": ["jsa"],
    "hazard identification risk assessment and determining control": ["hiradc", "hira"],
    
    # Property & Construction Specific Synonyms
    "rencana anggaran biaya": ["rab", "estimasi biaya", "cost estimation", "bill of quantity", "boq", "bq", "bill of quantities"],
    "autocad": ["cad", "auto cad", "autocad 2d", "autocad 3d", "computer aided design"],
    "3d modeling": ["sketchup", "3dmax", "3ds max", "sketch up", "google sketchup", "3d studio max"],
    "structural analysis": ["sap2000", "etabs", "tekla", "sap 2000", "etab", "tekla structures", "tekla structure"],
    "project management": ["ms project", "ms. project", "microsoft project", "primavera", "primavera p6"],
    "perjanjian pengikatan jual beli": ["ppjb"],
    "akta jual beli": ["ajb"],
    "izin mendirikan bangunan": ["imb"],
    "persetujuan bangunan gedung": ["pbg"],
    "sertifikat hak guna bangunan": ["shgb", "hgb"],
    "bea perolehan hak atas tanah dan bangunan": ["bphtb", "bea perolehan hak atas tanah"],

    # Finance & Accounting Specific
    "accurate": ["accurate online", "accurate 5", "accurate accounting"],
    "myob": ["myob premier", "myob accounting"],
    "quickbooks": ["quickbooks online"],
    "xero": ["xero accounting"],
    "jurnal": ["jurnal.id", "mekari jurnal"],
    "cpa": ["certified public accountant", "cpa indonesia"],
    "cfa": ["chartered financial analyst"],
    "ca": ["chartered accountant"],
    "cma": ["certified management accountant"],
    "cia": ["certified internal auditor"],
    "financial analysis": ["financial modeling", "financial projection", "analisis keuangan", "financial statement analysis", "analisis laporan keuangan"],
    "psak": ["pernyataan standar akuntansi keuangan"],
    "ifrs": ["international financial reporting standards"],
    "pembukuan": ["bookkeeping"],
    "cash flow management": ["cash flow", "arus kas"],
    "budgeting": ["penganggaran"],
    "e-faktur": ["efaktur"],
    "e-spt": ["espt"],
    "djp online": ["djponline"],
    "e-bupot": ["ebupot"],

    # Engineering Specific
    "revit": ["autodesk revit", "revit architecture", "revit structure"],
    "solidworks": ["solid works", "solidwork"],
    "archicad": ["archi cad"],
    "hvac": ["heating ventilation and air conditioning"],
    "plumbing": ["sistem perpipaan", "perpipaan"],
    "mep": ["mechanical electrical plumbing"],
    "project supervision": ["pengawasan proyek"],
    "k3 umum": ["ahli k3 umum", "ak3u", "sertifikat k3"],
    "k3 konstruksi": ["ahli k3 konstruksi"],
    "ska": ["sertifikat keahlian", "skt", "sertifikat keterampilan"],
    "sbu": ["sertifikat badan usaha"],
    "slf": ["sertifikat laik fungsi"],
    "gis": ["geographic information system", "sistem informasi geografis", "sig", "arcgis", "qgis"],

    # Healthcare & Medical
    "farmasi": ["pharmacy", "pharmaceutical"],
    "keperawatan": ["nursing", "perawat"],
    "fisioterapi": ["physiotherapy", "physical therapy"],
    "radiologi": ["radiology", "radiographer"],
    "rekam medis": ["medical record", "medical records"],
    "gizi": ["nutrition", "nutritionist", "ahli gizi"],
    "kesehatan masyarakat": ["public health", "kesmas"],
    "bpjs": ["bpjs kesehatan", "bpjs ketenagakerjaan"],

    # Legal & Compliance
    "legal drafting": ["penyusunan kontrak", "contract drafting", "drafting kontrak"],
    "due diligence": ["uji tuntas", "legal due diligence"],
    "notaris": ["notary", "notarial"],
    "litigasi": ["litigation"],
    "perizinan": ["licensing", "permit", "izin usaha"],

    # HR & People
    "rekrutmen": ["recruitment", "recruiting", "talent acquisition"],
    "penggajian": ["payroll", "gaji"],
    "kompensasi dan benefit": ["compensation & benefits", "compensation and benefits", "comben", "c&b"],
    "asesmen": ["assessment", "penilaian karyawan"],
    "hris": ["human resource information system"],
    "bpjs ketenagakerjaan": ["jamsostek"],

    # Education & Training
    "kurikulum": ["curriculum"],
    "pedagogi": ["pedagogy", "teaching methodology"],
    "paud": ["pendidikan anak usia dini", "early childhood education"],
    "lms": ["learning management system", "moodle", "google classroom"],

    # General Office & Admin
    "korespondensi": ["correspondence", "surat menyurat"],
    "pengarsipan": ["filing", "arsip", "kearsipan"],
    "notulensi": ["minutes", "notulen"],
    "administrasi umum": ["general affairs", "general admin", "ga"],

    # Supply Chain & Logistics
    "purchasing": ["pengadaan", "procurement"],
    "pengadaan barang": ["procurement", "purchasing"],
    "gudang": ["warehouse", "warehousing"],
    "inventory": ["persediaan", "stok", "inventory management"],
    "freight forwarding": ["ekspedisi", "shipping"],

    # Digital Marketing
    "google ads": ["adwords", "google adwords"],
    "facebook ads": ["meta ads", "fb ads"],
    "seo": ["search engine optimization"],
    "sem": ["search engine marketing"],
    "google analytics": ["ga4", "analytics"],
    "copywriting": ["copy writing", "penulisan naskah iklan"],
    "crm": ["customer relationship management", "salesforce", "hubspot"],

    # Sales Specific
    "negosiasi": ["negotiation", "teknik negosiasi", "negotiating"],
    "presentasi": ["presentation", "presenting", "keterampilan presentasi"],
    "lead generation": ["mencari prospek", "pencarian prospek", "prospecting"],
    "account management": ["manajemen akun", "client relationship"],
    "telemarketing": ["telesales", "telemarketing staff", "staf telemarketing"],

    # Marketing & Creative Specific
    "digital marketing": ["pemasaran digital", "online marketing", "internet marketing"],
    "social media marketing": ["manajemen media sosial", "social media management", "smm", "social media handling"],
    "content marketing": ["pemasaran konten"],
    "email marketing": ["pemasaran email", "mailchimp"],
    "brand strategy": ["strategi merek", "branding", "brand management"],
    "market research": ["riset pasar", "analisis pasar", "marketing research"],
    "content writing": ["content writer", "penulisan konten"],

    # Admin & General Office Specific
    "data entry": ["input data", "entri data", "pemasukan data"],
    "document control": ["pengendalian dokumen", "pengarsipan dokumen", "document controller"],
    "microsoft office": ["ms office", "office suite"],
    "google workspace": ["gsuite", "google docs", "google sheets", "google slides"],
    "office administration": ["administrasi kantor", "administrasi", "admin"],
    "scheduling": ["penjadwalan agenda", "calendar management", "penjadwalan"],
    "receptionist": ["resepsionis", "front desk", "penanganan telepon", "customer service desk"],

    # Healthcare
    "str": ["surat tanda registrasi"],
    "sip": ["surat izin praktik"],
    "btcls": ["basic trauma cardiac life support"],
    "acls": ["advanced cardiac life support"],
    "bls": ["basic life support", "cpr"],
    "patient care": ["perawatan pasien", "home care"],

    # Legal
    "corporate legal": ["legal korporasi", "hukum perusahaan"],
    "hubungan industrial": ["industrial relations", "ketenagakerjaan"],
    "upa": ["ujian profesi advokat", "peradi", "lisensi advokat"],
    "compliance": ["kepatuhan", "legal compliance"],

    # Education (Minimal)
    "ppg": ["pendidikan profesi guru"],
    "sertifikasi guru": ["sertifikasi pendidik", "serdik"],

    # Blue-Collar / Operational
    "gada pratama": ["sertifikat gada pratama", "pelatihan gada pratama"],
    "gada madya": ["sertifikat gada madya"],
    "gada utama": ["sertifikat gada utama"],
    "sim a": ["surat izin mengemudi a"],
    "sim b1": ["surat izin mengemudi b1", "sim b"],
    "sim b2": ["surat izin mengemudi b2"],
    "sim c": ["surat izin mengemudi c"],
    "sio forklift": ["surat izin operasional forklift"],
    "housekeeping": ["tata graha"],
    "gardening": ["berkebun", "lanskap", "pemeliharaan tanaman"],
}


def _apply_symbol_normalization(text: str) -> str:
    """Menerapkan normalisasi simbol pada teks keahlian mentah.

    Mengganti karakter khusus (seperti ++, #, titik pada framework)
    menjadi bentuk alfanumerik sebelum proses lookup sinonim.

    Parameter:
        text (str): Teks keahlian mentah dalam huruf kecil.

    Return:
        str: Teks yang telah dinormalisasi simbolnya.
    """
    for symbol, replacement in SYMBOL_NORMALIZATION_MAP.items():
        if text == symbol:
            return replacement
    return text


def normalize_skill(skill: str) -> str:
    """Menormalisasi string keahlian menggunakan peta simbol dan kamus sinonim.

    Alur normalisasi:
    1. Strip dan lowercase.
    2. Terapkan normalisasi simbol (c++ → cpp, .net → dotnet).
    3. Cocokkan dengan kamus sinonim (reactjs → react).
    4. Jika tidak ditemukan, kembalikan hasil normalisasi simbol apa adanya.

    Parameter:
        skill (str): String keahlian mentah dari CV atau JD.

    Return:
        str: Representasi kanonik dalam huruf kecil, atau string asli jika tidak ditemukan di kamus.
    """
    if not skill:
        return ""
    skill_lower = skill.strip().lower()

    # Tahap 1: Normalisasi simbol
    skill_normalized = _apply_symbol_normalization(skill_lower)

    # Tahap 2: Lookup kamus sinonim (gunakan hasil normalisasi simbol)
    for canonical, synonyms in SKILL_SYNONYMS.items():
        if skill_normalized == canonical or skill_normalized in synonyms:
            return canonical
        # Cek juga input asli (sebelum normalisasi simbol) untuk backward compatibility
        if skill_lower == canonical or skill_lower in synonyms:
            return canonical

    return skill_normalized


def get_skill_synonyms(skill: str) -> list[str]:
    """Mengembalikan semua variasi nama (sinonim) dari suatu keahlian,

    termasuk nama kanoniknya dan nama aslinya dalam huruf kecil.

    Parameter:
        skill (str): Nama keahlian yang akan dicari sinonimnya.

    Return:
        list[str]: Daftar variasi nama keahlian dalam huruf kecil.
    """
    if not skill:
        return []
    
    skill_lower = skill.strip().lower()
    canonical = normalize_skill(skill)
    
    synonyms = {skill_lower, canonical}
    
    if canonical in SKILL_SYNONYMS:
        synonyms.update(s.lower() for s in SKILL_SYNONYMS[canonical])
        
    return list(synonyms)


# ── Kelompok Keahlian Sejenis (Skill Clusters) Lintas Industri ────────────────
SKILL_CLUSTERS: list[set[str]] = [
    # 1. IT - PHP Frameworks
    {"laravel", "codeigniter", "symfony", "yii", "cakephp", "phalcon"},
    # 2. IT - Frontend Frameworks
    {"react", "vue", "angular", "svelte", "nextjs", "nuxtjs", "reactjs", "vuejs", "angularjs"},
    # 3. IT - Mobile Development
    {"flutter", "react native", "swift", "kotlin", "android sdk", "ios sdk"},
    # 4. IT - Databases
    {"postgresql", "mysql", "mariadb", "sqlite", "oracle", "mssql", "sql server", "mongodb", "redis", "postgres", "psql"},
    # 5. IT - Cloud Platforms
    {"aws", "gcp", "azure", "google cloud platform", "amazon web services", "microsoft azure", "google cloud"},
    # 6. IT - Deep Learning
    {"tensorflow", "pytorch", "keras", "tf"},
    # 7. IT - Python Web
    {"django", "flask", "fastapi"},
    
    # 8. Finance - Accounting Software
    {"sap", "accurate", "myob", "quickbooks", "xero", "jurnal", "jurnal.id"},
    # 9. Finance - Pajak/Tax Tools
    {"e-spt", "e-faktur", "brevet pajak", "brevet a", "brevet b", "brevet c", "efaktur", "espt"},
    
    # 10. Engineering & Construction - CAD/3D
    {"3d modeling", "autocad", "sketchup", "archicad", "solidworks", "revit", "3ds max", "sketch up", "auto cad", "autocad 2d", "autocad 3d", "computer aided design", "autodesk revit", "revit architecture", "revit structure", "solid works", "solidwork", "3d max", "3dsmax", "3d studio max", "archi cad"},
    # 11. Engineering & Construction - Structural Analysis
    {"structural analysis", "sap2000", "etabs", "tekla", "sap 2000", "etab", "tekla structures", "tekla structure"},
    # 12. Engineering & Construction - Project Management
    {"project management", "ms project", "primavera", "microsoft project", "ms. project", "primavera p6"},
    
    # 13. Creative & Design - Graphic
    {"photoshop", "illustrator", "coreldraw", "indesign", "canva", "adobe photoshop", "adobe illustrator"},
    # 14. Creative & Design - UI/UX
    {"figma", "adobe xd", "sketch"},
    # 15. Creative & Design - Video
    {"premiere", "after effects", "final cut", "davinci resolve", "adobe premiere"},
    
    # 16. Office - Spreadsheet
    {"excel", "microsoft excel", "google sheets", "ms excel"},
    # 17. Office - Word Processing
    {"word", "microsoft word", "google docs", "ms word"},

    # 18. Healthcare & Medical Tools
    {"spss", "stata", "epi info", "epidemiologi"},
    # 19. Legal
    {"legal drafting", "contract drafting", "due diligence", "litigasi"},
    # 20. HR Tools
    {"talenta", "gadjian", "workday", "bamboohr", "hris"},
    # 21. Construction Estimation
    {"rencana anggaran biaya", "quantity surveyor", "bill of quantity", "estimasi biaya"},
    # 22. GIS & Surveying
    {"arcgis", "qgis", "google earth", "pemetaan"},
    # 23. Tax & Audit
    {"pajak", "audit", "perpajakan", "brevet pajak", "e-spt", "e-faktur", "tax compliance", "kepatuhan pajak", "espt", "efaktur", "brevet a", "brevet b", "brevet c"},
    # 24. ERP Systems
    {"sap", "oracle erp", "odoo", "microsoft dynamics"},
    # 25. Digital Marketing
    {"google ads", "facebook ads", "meta ads", "seo", "sem", "google analytics", "digital marketing", "social media marketing", "content marketing", "email marketing", "brand strategy", "market research", "copywriting", "content writing"},
    # 26. Content Creation
    {"canva", "capcut", "adobe premiere", "copywriting", "content writing"},
    # 27. Warehouse & Logistics
    {"wms", "warehouse management", "forklift", "inventory management"},
    # 28. Safety & Construction Certifications
    {"k3 umum", "k3 konstruksi", "ak3u", "sertifikat k3", "ska", "skt", "sbu", "slf"},
    # 29. Sales Skills
    {"negosiasi", "presentasi", "lead generation", "crm", "account management", "telemarketing", "sales", "business development"},
    # 30. Office Administration & Support
    {"korespondensi", "pengarsipan", "notulensi", "administrasi umum", "data entry", "document control", "microsoft office", "google workspace", "office administration", "scheduling", "receptionist", "excel", "word"},
    # 31. Healthcare Certifications
    {"str", "sip", "btcls", "acls", "bls", "patient care"},
    # 32. Legal Credentials & Skills
    {"upa", "corporate legal", "compliance", "hubungan industrial", "peradi", "legal drafting", "due diligence", "litigasi"},
    # 33. Blue-Collar Skills & Driver Licenses
    {"gada pratama", "gada madya", "gada utama", "sim a", "sim b1", "sim b2", "sim c", "sio forklift", "housekeeping", "gardening", "cleaning service"},
    # 34. Education Credentials (Minimal)
    {"ppg", "sertifikasi guru", "kurikulum", "pedagogi"},
]


def are_skills_similar(skill_a: str, skill_b: str) -> bool:
    """Memeriksa apakah dua keahlian berada dalam satu kelompok keahlian sejenis (Skill Cluster) yang sama.

    Parameter:
        skill_a (str): Nama keahlian pertama.
        skill_b (str): Nama keahlian kedua.

    Return:
        bool: True jika kedua keahlian berada di kelompok yang sama, False jika tidak.
    """
    if not skill_a or not skill_b:
        return False
        
    norm_a = normalize_skill(skill_a)
    norm_b = normalize_skill(skill_b)
    
    if not norm_a or not norm_b:
        return False
        
    for cluster in SKILL_CLUSTERS:
        if norm_a in cluster and norm_b in cluster:
            return True
            
    return False

