import pytest
from core.filtering.semantic_matcher import semantic_matcher

def test_semantic_capability_report():
    """
    Test ini bukan untuk CI/CD pipeline reguler (karena tidak ada assert ketat), 
    melainkan untuk melaporkan skor kemiripan semantik ke konsol agar developer
    bisa memvalidasi 'intuisi' model NLP.
    """
    print("\n\n" + "="*50)
    print("LAPORAN KEMAMPUAN SEMANTIK (multilingual-e5-base)")
    print("="*50)

    # Pastikan model diinisialisasi
    semantic_matcher.initialize()

    test_cases = [
        # 1. Sinonim Leksikal (Teks berbeda, makna sama)
        ("Human Resources", "HR", "Sinonim Leksikal"),
        ("Machine Learning", "Artificial Intelligence", "Sinonim Leksikal"),
        ("Frontend Developer", "UI/UX Designer", "Related Domain"),
        
        # 2. Lintas Bahasa (Multilingual)
        ("Software Engineer", "Rekayasa Perangkat Lunak", "Multilingual"),
        ("Web Developer", "Pengembang Web", "Multilingual"),
        ("Tax Accounting", "Akuntansi Pajak", "Multilingual"),
        
        # 3. Kata Mengecoh (Teks mirip, makna beda)
        ("Java", "JavaScript", "Mengecoh (Mirip)"),
        ("C", "C++", "Mengecoh (Mirip)"),
        ("Car", "Carpet", "Mengecoh (Mirip)"),
        
        # 4. Singkatan Industri Khusus
        ("Estimasi Biaya", "RAB", "Industri Khusus"),
        ("Kesehatan Keselamatan Kerja", "K3", "Industri Khusus"),
        ("Food & Beverage", "F&B", "Industri Khusus"),

        # 5. Konsep Jauh sama sekali
        ("Data Scientist", "Cleaning Service", "Unrelated"),
        ("Backend Developer", "Supir Truk", "Unrelated"),
    ]

    for word1, word2, category in test_cases:
        score, _ = semantic_matcher.calculate_max_similarity(word1, [word2])
        
        # > 0.85 (Tinggi), 0.70-0.84 (Sedang), < 0.70 (Rendah)
        eval_str = "TINGGI" if score >= 0.85 else "SEDANG" if score >= 0.75 else "RENDAH"
        
        print(f"[{category:^18}] {word1:<28} vs {word2:<25} -> {score:.4f} ({eval_str})")
        
    print("="*50 + "\n")
