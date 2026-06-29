"""Major group mapping and education hierarchy for rule-based filtering."""

# Mapping jurusan serumpun — jika jurusan kandidat ada di group yang sama
# dengan jurusan yang dibutuhkan, dianggap match (saat major_flexibility = "flexible")
MAJOR_GROUPS: dict[str, list[str]] = {
    "Teknik Informatika": [
        "Ilmu Komputer", "Sistem Informasi", "Teknik Komputer",
        "Rekayasa Perangkat Lunak", "Teknologi Informasi",
        "Informatika", "Computer Science", "Information Systems",
        "Teknik Perangkat Lunak",
    ],
    "Teknik Elektro": [
        "Teknik Elektronika", "Teknik Listrik", "Teknik Tenaga Listrik",
        "Electrical Engineering", "Teknik Telekomunikasi",
    ],
    "Akuntansi": [
        "Manajemen Keuangan", "Ekonomi Akuntansi", "Perpajakan",
        "Keuangan", "Akuntansi Perpajakan", "Ekonomi",
    ],
    "Manajemen": [
        "Administrasi Bisnis", "Bisnis", "MBA", "Manajemen Bisnis",
        "Business Administration", "Manajemen SDM",
        "Manajemen Sumber Daya Manusia",
    ],
    "Psikologi": [
        "Psikologi Industri", "Psikologi Klinis", "Psikologi Organisasi",
    ],
    "Teknik Industri": [
        "Teknik Manufaktur", "Teknik Produksi", "Industrial Engineering",
    ],
    "Administrasi Publik": [
        "Administrasi Negara", "Ilmu Administrasi Negara", "Ilmu Administrasi Publik",
        "Kebijakan Publik", "Public Administration", "State Administration",
    ],
}

# Hierarchy jenjang pendidikan — semakin tinggi angka, semakin tinggi jenjang
# D4 setara S1 (keduanya level 4)
EDUCATION_HIERARCHY: dict[str, int] = {
    "SMA": 1, "SMK": 1,
    "D1": 2, "D2": 2, "D3": 3,
    "D4": 4, "S1": 4,
    "S2": 5,
    "S3": 6,
}

# Single source of truth — mapping education_id (dari DB) ke string jenjang
# Sebelumnya didefinisikan terpisah di hard_filter.py, filtering.py, dan formatter.py
EDU_ID_TO_STR: dict[int, str] = {
    1: "SD", 2: "SMP", 3: "SMA", 4: "D1", 5: "D2",
    6: "D3", 7: "D4", 8: "S1", 9: "S2", 10: "S3",
}

# Kamus terjemahan/sinonim jurusan untuk normalisasi saat pencocokan (strict major filter)
MAJOR_SYNONYMS: dict[str, str] = {
    # IT & Computer Science (Disatukan ke nama kanonis untuk menghindari kendala bahasa Inggris/Indonesia)
    "informatics": "Teknik Informatika",
    "informatics engineering": "Teknik Informatika",
    "informatika": "Teknik Informatika",
    "teknik informatika": "Teknik Informatika",
    "computer science": "Teknik Informatika",
    "ilmu komputer": "Teknik Informatika",
    
    "information systems": "Sistem Informasi",
    "sistem informasi": "Sistem Informasi",
    
    "information technology": "Teknologi Informasi",
    "teknologi informasi": "Teknologi Informasi",
    "it": "Teknologi Informasi",
    
    "software engineering": "Rekayasa Perangkat Lunak",
    "rekayasa perangkat lunak": "Rekayasa Perangkat Lunak",
    
    "computer engineering": "Teknik Komputer",
    "teknik komputer": "Teknik Komputer",
    
    # Engineering
    "electrical engineering": "Teknik Elektro",
    "teknik elektro": "Teknik Elektro",
    "mechanical engineering": "Teknik Mesin",
    "teknik mesin": "Teknik Mesin",
    "civil engineering": "Teknik Sipil",
    "teknik sipil": "Teknik Sipil",
    "industrial engineering": "Teknik Industri",
    "teknik industri": "Teknik Industri",
    "chemical engineering": "Teknik Kimia",
    "teknik kimia": "Teknik Kimia",
    "environmental engineering": "Teknik Lingkungan",
    "teknik lingkungan": "Teknik Lingkungan",
    "physics engineering": "Teknik Fisika",
    "teknik fisika": "Teknik Fisika",
    "architectural engineering": "Teknik Arsitektur",
    "teknik arsitektur": "Teknik Arsitektur",
    
    # Business & Economics
    "accounting": "Akuntansi",
    "akuntansi": "Akuntansi",
    "management": "Manajemen",
    "manajemen": "Manajemen",
    "business administration": "Administrasi Bisnis",
    "administrasi bisnis": "Administrasi Bisnis",
    "ilmu administrasi bisnis": "Administrasi Bisnis",
    "administrasi niaga": "Administrasi Bisnis",
    "ilmu administrasi niaga": "Administrasi Bisnis",
    "public administration": "Administrasi Publik",
    "administrasi publik": "Administrasi Publik",
    "ilmu administrasi publik": "Administrasi Publik",
    "administrasi negara": "Administrasi Publik",
    "ilmu administrasi negara": "Administrasi Publik",
    "state administration": "Administrasi Publik",
    "kebijakan publik": "Administrasi Publik",
    "ilmu kebijakan publik": "Administrasi Publik",
    "public policy": "Administrasi Publik",
    "economics": "Ekonomi",
    "ekonomi": "Ekonomi",
    "finance": "Keuangan",
    "keuangan": "Keuangan",
    
    # SDM / Human Resources (Semua varian dinormalisasi ke "Manajemen SDM")
    "sdm": "Manajemen SDM",
    "sumber daya manusia": "Manajemen SDM",
    "manajemen sdm": "Manajemen SDM",
    "manajemen sumber daya manusia": "Manajemen SDM",
    "msdm": "Manajemen SDM",
    "human resource management": "Manajemen SDM",
    "human resources": "Manajemen SDM",
    "hrm": "Manajemen SDM",
    "hr management": "Manajemen SDM",
    
    # Creative & Design
    "dkv": "Desain Komunikasi Visual",
    "desain komunikasi visual": "Desain Komunikasi Visual",
    "visual communication design": "Desain Komunikasi Visual",
    "vcd": "Desain Komunikasi Visual",
    "interaction design": "Interaction Design",
    "desain interaksi": "Interaction Design",
    "product design": "Desain Produk",
    "desain produk": "Desain Produk",
    "graphic design": "Desain Grafis",
    "desain grafis": "Desain Grafis",

    # Humanities & Sciences
    "psychology": "Psikologi",
    "psikologi": "Psikologi",
    "statistics": "Statistika",
    "statistika": "Statistika",
    "mathematics": "Matematika",
    "matematika": "Matematika",
    "applied mathematics": "Matematika Terapan",
    "matematika terapan": "Matematika Terapan",
    "physics": "Fisika",
    "fisika": "Fisika",
    "chemistry": "Kimia",
    "kimia": "Kimia",
    "biology": "Biologi",
    "biologi": "Biologi",
    "law": "Hukum",
    "hukum": "Hukum",
    "english": "Bahasa Inggris",
    "bahasa inggris": "Bahasa Inggris",
}

