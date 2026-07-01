# Dokumentasi Sistem AI CV Filtering (Sistem Penyaringan Kandidat)

## 1. Ikhtisar Sistem
Sistem ini adalah microservice berbasis kecerdasan buatan (AI) yang bertugas menyaring, menilai, dan mengkategorikan kandidat (pelamar kerja) secara otomatis. Berbeda dengan ATS (*Applicant Tracking System*) tradisional yang murni mengandalkan pencocokan kata kunci, sistem ini memadukan **Pencocokan Semantik (*Semantic Matching*)** berbasis model representasi vektor dan **Aturan Bisnis HR Deterministik** untuk menghasilkan keputusan yang cerdas, cepat, presisi, dan dapat diaudit secara transparan.

Arsitektur sistem dirancang agar sepenuhnya deterministik dalam proses pemeringkatan, meminimalisasi halusinasi AI, serta menjamin stabilitas kecepatan pemrosesan pada volume pelamar skala tinggi (skala *enterprise*).

---

## 2. Arsitektur Pipa Penyaringan (*Filtering Pipeline*)
Proses penyaringan dieksekusi menggunakan *Orchestrator Pattern* di mana aliran data melewati serangkaian lapisan (*layer*) evaluasi yang saling berkesinambungan.

### Layer 1: Hard Filter (Penyaring Mutlak)
Fase eliminasi prediktif tahap awal untuk menggugurkan kandidat yang secara absolut tidak memenuhi prasyarat mendasar (non-negosiabel).
- **Pendidikan Minimal** (Misal: Lowongan mensyaratkan tingkat minimum S1).
- **Kecocokan Jurusan Akademik** (Mendukung pencocokan vektor semantik untuk rumpun keilmuan yang ekuivalen).
- **Batas Usia** (Rentang usia minimum dan maksimum).
- **Pengalaman Kerja** (Minimum durasi masa kerja agregat).
- **IPK Minimal** (Penyaringan ambang batas numerik).
- **Sertifikasi Wajib** (Pencocokan kepemilikan sertifikasi teknis mutlak dengan ambang batas ketat).
- **Status Pernikahan & Gender** (Jika diwajibkan secara spesifik oleh profil jabatan).

### Layer 1.5: Category Filter
Lapisan perlindungan pencegah (*false positive*) lintas industri. Filter ini memblokir kandidat yang riwayat pekerjaannya tidak beririsan secara logika bisnis dengan rumpun industri yang dituju, kecuali telah diizinkan melalui peta kompatibilitas industri yang didefinisikan secara khusus.

### Layer 2: Taxonomy Matcher (Kecocokan Peran Pekerjaan)
Memanfaatkan model bahasa matriks vektor (`intfloat/multilingual-e5-base`) untuk mengalkulasi kedekatan semantik riwayat jabatan kandidat terhadap standar taksonomi/peran yang dibuka. Sistem ini mencakup *logic* profil khusus:
- **Deteksi Job Hopping**: Sistem secara otomatis mengidentifikasi pola perpindahan pekerjaan yang terlalu masif dan cepat (durasi rata-rata < 12 bulan per posisi) serta menerapkan sistem penalti kedisiplinan berjenjang.

### Layer 3: Skills Filter (Filter Keahlian)
Mencocokkan keahlian inti (*hard skills*) yang diekstrak secara otomatis oleh model AI dari narasi riwayat pendidikan, riwayat pekerjaan, dan riwayat pelatihan kandidat.
- **Kandidat Senior (Berpengalaman):** Sistem menerapkan validasi terhadap keberadaan keahlian wajib dalam riwayat pekerjaan mereka.
- **Fresh Graduate:** Ambang batas relevansi (*similarity threshold*) dilonggarkan guna mengakomodir kesenjangan penulisan istilah teknis pada riwayat akademis/pendidikan mereka.

### Layer 4: Scoring & Tiering
Fase rekapitulasi matematis guna menghasilkan skor akhir (skala 0 - 100) melalui formula bobot adaptif:
- **Jabatan Senior:** Bobot masa kerja sangat dominan.
- **Entry-Level/Fresh Graduate:** Pengalaman direduksi, sebaliknya bobot almamater/pendidikan, IPK, dan keahlian dioptimalisasi secara otomatis.
- **Incomplete Profile Penalty:** Pinalti skor sebesar 30% bagi kandidat baru yang tag dan keahlian semantiknya belum sempat diekstraksi oleh *worker* asinkron AI.

Skor akhir (*raw score*) kemudian diregistrasi secara sistematis ke dalam tiga jenjang keputusan:
1. **LAYAK:** Skor 50.0 - 100.0 (Kandidat representatif).
2. **REVIEW:** Skor 30.0 - 49.9 (Kualifikasi parsial, diinstruksikan untuk audit manual oleh HRD).
3. **ALTERNATIF:** Skor 0 - 29.9 (Kandidat yang tidak memenuhi kriteria inti, diparkir sebagai cadangan strategis).

Setiap tahapan penyesuaian skor menyimpan jejak historis degradasi di sistem guna memudahkan proses *audit trail* oleh tim HRD.

---

## 3. Komponen Teknologi Utama (Tech Stack)
- **Application Framework:** FastAPI (Python 3.12)
- **Database Engine:** PostgreSQL (Terintegrasi via SQLAlchemy Async ORM)
- **Memory Cache & Message Broker:** Redis
- **Background Task Processing:** Celery
- **Semantic Vector Embeddings:** HuggingFace `intfloat/multilingual-e5-base` (Untuk pencocokan semantik di dalam *Pipeline Deterministik*).
- **Large Language Model (LLM):** Qwen3.5-4B (Didedikasikan secara eksklusif dalam lingkungan asinkron untuk fase prapemrosesan *Job Description* & standarisasi label entitas data pengguna, memastikan agar volatilitas eksekusi LLM tidak memberikan latensi pada perulangan filter penyaringan utama).

---

## 4. Keamanan & Reliabilitas Kode
Proyek ini mengadopsi prosedur kualitas standar *Enterprise* dengan karakteristik sebagai berikut:
- **Desain Deklaratif:** Inti pemrosesan tidak berjalan dalam struktur fungsi yang monolitik (seperti *God Functions*), melainkan dikelola dengan *Orchestrator* bersih yang mendistribusikan tahapan secara tersegregasi.
- **Test-Driven Reliability:** Melibatkan unit testing, pengujian tekanan (*stress-test*), hingga *Integration Accuracy Test* di setiap jalur percabangan logika penyaringan guna menghindari pergeseran (*regressions*) saat pembaruan skor.
- **Otorisasi Terpusat:** Diisolasi penuh dalam jaringan, dengan pembatasan kunci otentikasi API rahasia (*Granular API Keys*) lintas layanan sistem pusat.

## 5. Struktur Database & Tipe Data
Sistem ini membedakan tabel menjadi dua kelompok: **Read-Only** (bersumber dari sistem web portal HR utama) dan **Read-Write** (dimiliki dan dikelola secara eksklusif oleh sistem AI ini).

### Tabel Read-Only (Referensi dari Portal Utama)
Sistem hanya membaca data dari tabel ini (sebagai fondasi data pelamar).

#### 1. `job_vacancy`
Menyimpan informasi lowongan pekerjaan.
- `job_vacancy_id` (Integer, Primary Key)
- `job_vacancy_name` (Varchar/String): Nama jabatan, misal: *"Senior Backend Engineer"*
- `job_vacancy_job_desc` (Text): Deskripsi pekerjaan mentah
- `job_vacancy_job_spec` (Text): Spesifikasi/kualifikasi mentah

#### 2. `require`
Menyimpan data identitas pelamar/kandidat.
- `requireid` (Integer, Primary Key)
- `firstname`, `lastname` (String): Nama kandidat
- `dateofbirth` (String/Date): Tanggal lahir (sistem mendukung parsing berbagai format string tanggal Indonesia)
- `gender` (String): Jenis kelamin, misal: *"Pria"*
- `maritalstatus` (String): Status pernikahan, misal: *"Lajang"*

#### 3. `requireeducation`, `requireworkexperience`, `requiretraining`
Menyimpan riwayat pendidikan, pekerjaan, dan sertifikasi kandidat. Tipe datanya umumnya `String` untuk nama institusi/perusahaan dan `Date`/`Integer` untuk durasi/tahun.

---

### Tabel Read-Write (Milik Layanan AI)
Dibuat otomatis oleh SQLAlchemy (`metadata.create_all`).

#### 1. `parsed_job_cache`
Menyimpan hasil ekstraksi LLM dari teks deskripsi lowongan agar sistem tidak perlu memanggil LLM berulang kali saat menyaring ribuan kandidat.
- `id` (Integer, PK)
- `job_vacancy_id` (Integer, FK -> job_vacancy)
- `parsed_requirements` (JSONB): Konversi terstruktur dari teks. 
  *Contoh:* `{"min_experience_years": 3, "required_skills": ["Python", "PostgreSQL"], "allowed_majors": ["Teknik Informatika"]}`
- `tags` (JSONB): Tag pekerjaan otomatis. *Contoh:* `["IT & Software", "Engineering"]`

#### 2. `candidate_skills`
Menyimpan hasil ekstraksi keahlian dari pelamar (distandarisasi oleh AI).
- `id` (Integer, PK)
- `require_id` (Integer, FK -> require)
- `hard_skill` (Text): Kumpulan keahlian teknis dipisahkan koma. *Contoh:* `"Java, Spring Boot, Redis"`

#### 3. `filtering_results`
Log atau jejak audit (*audit trail*) hasil penyaringan kandidat terhadap suatu lowongan.
- `id` (Integer, PK)
- `job_vacancy_id` (Integer, FK)
- `require_id` (Integer, FK)
- `candidate_name` (String)
- `stage` (String): Tahapan saat eliminasi. *Contoh:* `"skills_filter"`, `"taxonomy_filter"`
- `decision` (String): Tier keputusan akhir. *Enum:* `"LAYAK"`, `"REVIEW"`, `"ALTERNATIF"`, `"ELIMINATED"`
- `reason` (Text): Alasan transparan yang dihasilkan sistem. *Contoh:* `"[Pendidikan] Pendidikan terakhir (SMA) di bawah kualifikasi minimum (S1)."`
- `total_score` (Float): Skor akhir kecocokan kandidat. *Contoh:* `85.5`
- `score_breakdown` (JSONB): Penjabaran komponen nilai (pendidikan, pengalaman, skill) untuk UI/Frontend.
- `confidence` (String): Tingkat keyakinan sistem. *Enum:* `"high"`, `"medium"`, `"low"`

---

## 6. Dokumentasi API (Endpoints)
Semua permintaan API dari *frontend* atau *backend* utama diwajibkan menyertakan *header* autentikasi keamanan.

### 1. Eksekusi Penyaringan Penuh
Menjalankan *filtering pipeline* terhadap kandidat yang melamar pada lowongan spesifik. Sistem akan mengeksekusi Layer 1 hingga 4 dan menyimpan hasilnya ke database.
- **URL**: `/api/v1/filtering/run`
- **Method**: `POST`
- **Headers**: `x-api-key: <API_KEY_FILTERING>`
- **Query Params**:
  - `job_vacancy_id` (Integer, Wajib)
  - `mode` (String, Opsional): `"registered"` (default, hanya pelamar pada lowongan ini) atau `"mixmatch"` (mencari kecocokan dari seluruh database kandidat aktif).

**Contoh Response Sukses (200 OK):**
```json
{
  "job_vacancy_id": 101,
  "job_tags": ["IT", "Software Development"],
  "total_candidates": 50,
  "after_hard_filter": 30,
  "after_taxonomy_filter": 25,
  "duration_seconds": 2.34,
  "candidates": [
    {
      "candidate_id": 502,
      "name": "Budi Santoso",
      "education": { "level": "S1", "major": "Teknik Informatika", "university": "Universitas A" },
      "experiences": [
        { "job_title": "Backend Developer", "company": "PT Tech", "duration_months": 24 }
      ],
      "total_score": 92.5,
      "decision": "LAYAK",
      "confidence": "high",
      "match_reason": "Kandidat memenuhi seluruh kualifikasi wajib (S1, IPK 3.5, 2 tahun pengalaman) dan memiliki 100% hard skills yang dicari."
    }
  ]
}
```

### 2. Mengambil Hasil Penyaringan (Cache)
Digunakan oleh aplikasi HRD untuk sekadar melihat daftar kandidat yang lolos tanpa menjalankan ulang proses perhitungan AI yang memakan waktu.
- **URL**: `/api/v1/filtering/results/{job_vacancy_id}`
- **Method**: `GET`
- **Headers**: `x-api-key: <API_KEY_FILTERING>`
- **Response**: Mirip dengan payload `/run`, namun memuat langsung dari tabel `filtering_results`.

### 3. Ekstraksi Tag Otomatis (Background Task)
Memicu *worker* Celery secara asinkron untuk mengekstrak dan menstandarisasi profil kandidat yang baru saja mendaftar (namun belum memiliki label/tag semantik).
- **URL**: `/api/v1/candidates/trigger-extraction`
- **Method**: `POST`
- **Headers**: `x-api-key: <API_KEY_EXTRACT_TAGGER>`
- **Response**: `{"message": "Extraction process started for 15 candidates"}`

### 4. Mendapatkan Daftar Kandidat yang Gugur (Eliminated)
Melihat rekapitulasi siapa saja yang dieliminasi secara mutlak beserta alasan presisi dari fase *Hard Filter* atau *Category Filter*.
- **URL**: `/api/v1/filtering/eliminated/{job_vacancy_id}`
- **Method**: `GET`
- **Headers**: `x-api-key: <API_KEY_FILTERING>`
- **Response**:
```json
[
  {
    "stage": "hard_filter",
    "candidate_name": "Siti Aminah",
    "reason": "[Usia] Usia kandidat (36) melebihi batas maksimal (35)."
  }
]
```

## 7. Penanganan Anomali (Edge Cases Handling)
Sistem ini telah dirancang untuk tidak kaku dan mampu menghadapi ketidaksempurnaan data di lapangan. Berikut adalah skenario anomali ekstrem yang sering terjadi pada platform rekrutmen dan bagaimana arsitektur AI ini mengatasinya:

### Kasus 1: *Fresh Graduate* Melamar Posisi yang Mensyaratkan Keahlian
- **Masalah:** Lulusan baru biasanya belum memiliki keahlian teknis spesifik yang setara dengan profesional senior (misal belum terbiasa dengan arsitektur mikroservis tingkat lanjut).
- **Penanganan Sistem:** Sistem secara otomatis mendeteksi status *Fresh Graduate* jika total pengalaman kerja kurang dari 1 tahun. Jika terdeteksi, AI mengaktifkan protokol pelonggaran (*Threshold Relaxation*). Sistem tidak akan memblokir mereka di *Skills Filter*, melainkan menurunkan bobot pengalaman kerjanya dan mengkompensasinya dengan meningkatkan bobot IPK dan relevansi pendidikan akademik.

### Kasus 2: Kutu Loncat (*Job Hopper*)
- **Masalah:** Kandidat memiliki total pengalaman kerja 5 tahun, namun sering berpindah-pindah 8 perusahaan dalam kurun waktu tersebut. ATS tradisional akan menilainya memiliki pengalaman 5 tahun penuh dan memberikannya skor tinggi.
- **Penanganan Sistem:** Di dalam *Taxonomy Matcher* (Layer 2), sistem menghitung rasio masa kerja per perusahaan. Jika rata-ratanya di bawah 12 bulan (1 tahun), kandidat akan ditandai secara internal sebagai *Job Hopper* dan skor stabilitas karirnya akan dipotong. Keputusan HRD untuk meloloskannya menjadi lebih berhati-hati.

### Kasus 3: Kandidat Baru yang Datanya Belum Diekstrak oleh AI (*Incomplete Profile*)
- **Masalah:** Karena data wajib seperti Umur, IPK, dan Tanggal Lahir diwajibkan diisi pada form registrasi portal lowongan kerja, data-data dasar tersebut dipastikan tidak akan pernah kosong. Namun, ada kemungkinan kandidat yang baru mendaftar langsung disaring sebelum *background worker* asinkron (Celery) selesai memproses ekstraksi tag semantik (`candidate_tags` masih bernilai kosong/None).
- **Penanganan Sistem:** Sistem tidak akan *crash* atau menolak kandidat tersebut. Sistem akan tetap menyaring mereka menggunakan data dasar terstruktur yang tersedia (Pendidikan, Masa Kerja, IPK asli). Tetapi, sistem akan memberikan **Incomplete Profile Penalty** (pengurangan skor total sebesar 30%) dan menurunkan tingkat keyakinan sistem menjadi **low** sebagai penanda bagi HRD bahwa profil kandidat ini masih dalam antrean ekstraksi keahlian oleh AI.

### Kasus 4: Kesalahan Ketik atau Perbedaan Sinonim (*Vocabulary Mismatch*)
- **Masalah:** Perusahaan mencari "Backend Developer" atau mewajibkan skill "Golang". Kandidat menulis di profilnya "Server Engineer" dan menguasai "Go Programming Language". Sistem ATS berbasis *keyword* pasti akan menggugurkannya.
- **Penanganan Sistem:** Karena AI menggunakan pencocokan **Semantik Vektor (Vector Embeddings)** dari HuggingFace, sistem memahami bahwa "Backend Developer" secara matematis sama maknanya dengan "Server Engineer". Begitu pula dengan "Golang" dan "Go". Kandidat ini akan tetap lolos dengan probabilitas *Similarity Score* di atas 90%.

### Kasus 5: Kandidat dengan Pengalaman Relevan namun Tanpa Eksplisit Skill Terdaftar
- **Masalah:** Di job portal tidak terdapat formulir pengisian data keahlian (*skills*), data organisasi, maupun data proyek secara khusus. Data keahlian, sertifikasi, dan riwayat pekerjaan kandidat murni ditarik dari riwayat pekerjaan (*work experience*), riwayat pendidikan (*education*), dan riwayat pelatihan (*training*) yang ditulis secara naratif/tekstual. Jika kandidat menulis riwayat kerja sebagai *Senior Frontend Developer* namun tidak menuliskan secara eksplisit kata/term teknologi spesifik seperti "ReactJS" di dalam deskripsi pekerjaannya, ATS berbasis keyword biasa akan langsung mendepaknya dari penyaringan jika lowongan menetapkan "ReactJS" sebagai keahlian wajib.
- **Penanganan Sistem:** LLM pada pipa pra-proses mengekstrak keahlian kandidat secara asinkron dari kalimat deskripsi pekerjaan, pendidikan, dan pelatihan. Pada pipa filter utama, jika kandidat tidak memuat keahlian spesifik tersebut namun secara *Taxonomy Role* (jabatan riwayat kerjanya) teridentifikasi *Exact Match* (sangat cocok) dengan peran lowongan, sistem penyaringan tidak akan mengeliminasi kandidat tersebut. Sistem akan menyelamatkannya dan memindahkannya ke kelompok **ALTERNATIF** (bukan langsung gugur), sehingga HRD tetap mendapatkan rekomendasi kandidat potensial.

### Kasus 6: Koneksi ke Model Bahasa (LLM) Terputus/Mati
- **Masalah:** Server tempat Qwen3.5-4B beroperasi sedang *down* (kehabisan GPU / *timeout*).
- **Penanganan Sistem:** Proses penyaringan ratusan pelamar (*run filtering*) **tidak akan terhenti**. Ekstraksi teks hanya dibutuhkan sekali saat pembacaan deskripsi lowongan pertama kali, yang kemudian hasilnya langsung disimpan selamanya di tabel `parsed_job_cache`. Selama *cache* ini ada, sistem deterministik akan berjalan sendiri secepat kilat tanpa perlu memanggil LLM sama sekali.

### Kasus 7: Judul Jabatan Modern/Non-Standar (Misal: *MT*, *Management Trainee*, *Junior Developer*)
- **Masalah:** Kandidat menulis riwayat jabatannya dengan istilah modern atau singkatan yang tidak terdaftar di KBJI/ISCO resmi, sehingga sistem tidak bisa memetakan rumpun karirnya secara tepat.
- **Penanganan Sistem:** Sistem mengadopsi normalisasi bertingkat (*Tiered Normalization*):
  1. **Pencocokan Eksak:** Mencari kecocokan langsung pada kamus aliases.
  2. **Pencocokan Regex:** Mengurai kata kunci sebagian (seperti mengupas "Senior Python Developer" menjadi "Python Developer" agar terdeteksi).
  3. **Pencocokan Semantik Vektor:** Mencari kedekatan makna linguistik ke kode ISCO terdekat menggunakan model embedding jika langkah 1 & 2 nihil.
  4. **Protokol *Unknown*:** Jika semua langkah gagal, sistem **tidak akan crash**, melainkan menandai jabatan tersebut sebagai *unknown*, membatasi skor maksimal di angka 25.0 (karena keahlian karir tidak terverifikasi), dan menyimpannya dengan aman agar bisa diulas HRD.

### Kasus 8: Risiko *Database Connection Leak* Akibat Proses Asinkron/Panggilan Eksternal yang Lambat
- **Masalah:** Server AI memproses ribuan antrean transaksi. Jika *database connection pool* terus ditahan saat sistem menunggu respons model bahasa/LLM eksternal (yang bisa memakan waktu hingga puluhan detik), server akan mengalami *deadlock* (kehabisan jalur koneksi database).
- **Penanganan Sistem:** Orkestrator `run_filtering` dirancang dengan pemisahan sesi database yang disiplin. Sebelum memanggil evaluasi LLM asinkron (jika diaktifkan), sistem akan melakukan *commit* dan menutup sesi database aktif (`await db.close()`). Setelah LLM selesai merespons, sistem akan membuka sesi transaksi baru yang bersih untuk menyimpan hasil akhir (`_save_final_results`). Hal ini menjamin *database pool* di server produksi Anda tetap longgar dan aman dari risiko *hang*.
