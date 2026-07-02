# Dokumentasi API Microservice Filtering Pelamar (Core AI)

Sistem CV-Filtering ini memiliki **4 API Utama** yang berfungsi sebagai mesin penggerak *Artificial Intelligence*. Seluruh rute dilindungi menggunakan mekanisme **API Key** pada header HTTP (`X-API-KEY`).

---

## DAFTAR ISI
1. [API 1: Candidate Tagger (Ekstraksi Profil)](#1-api-1-candidate-tagger-ekstraksi-profil)
2. [API 2: Job Parser (Bedah Lowongan)](#2-api-2-job-parser-bedah-lowongan)
3. [API 3: Filtering (Penyaringan Pelamar)](#3-api-3-filtering-penyaringan-pelamar)
4. [API 4: Mix-Match (Pencarian Talent Pool)](#4-api-4-mix-match-pencarian-talent-pool)
5. [API Pendukung (Status & Hasil)](#5-api-pendukung)

---

## 1. API 1: Candidate Tagger (Ekstraksi Profil)

Memicu AI (Qwen/LLM) untuk membaca data teks pelamar dari hasil pengisian form portal (tabel `require`), lalu mengekstraknya menjadi daftar keahlian (*skills*), pengalaman (*experience*), dan tag struktural.

### `POST /api/candidates/{user_id}/extract-tags`

- **Kapan Digunakan:** Segera setelah pelamar membuat akun, atau memperbarui profil form mereka di portal.
- **Header:** `X-API-KEY` (Gunakan `API_KEY_EXTRACT_TAGGER` dari `.env`)
- **Query Parameter:**
  - `sync` *(boolean, default: false)*: Jika `false`, berjalan instan via *background Celery*. Jika `true`, API akan *loading* 10-20 detik menunggu AI selesai.
- **Response (200 OK - Asinkron):**
```json
{
  "status": "processing",
  "require_id": 123,
  "message": "Proses ekstraksi tag dan skill sedang berjalan di latar belakang."
}
```

---

## 2. API 2: Job Parser (Bedah Lowongan)

Memicu AI untuk membedah teks lowongan pekerjaan (Job Description & Requirements), merapikan rentang umur, batas pengalaman, dan menentukan keahlian wajib (*Required*) vs nilai tambah (*Preferred*).

### `POST /api/jobs`

- **Kapan Digunakan:** Secara otomatis dipanggil di latar belakang oleh sistem saat fitur Filtering dijalankan pertama kali pada lowongan baru. Dapat juga dipanggil secara manual jika Anda ingin me-*refresh* hasil ekstraksi AI untuk spesifik 1 lowongan (`job_vacancy_id`) tertentu.
- **Header:** `X-API-KEY` (Gunakan `API_KEY_JOB_PARSER` dari `.env`)
- **Query Parameter:**
  - `sync` *(boolean, default: false)*: Set ke `true` jika ingin hasil langsung kembali.
- **Body JSON:**
```json
{
  "job_vacancy_id": 45,
  "title": "Backend Developer",
  "job_vacancy_job_desc": "Dibutuhkan developer Python...",
  "job_vacancy_job_spec": "Minimal S1, pengalaman 2 tahun"
}
```
- **Response (200 OK - Asinkron):**
```json
{
  "job_vacancy_id": 45,
  "title": "Backend Developer",
  "description": "Dibutuhkan developer Python...",
  "status": "processing",
  "message": "Parsing Job #45 dijadwalkan di latar belakang."
}
```

---

## 3. API 3: Filtering (Penyaringan Pelamar)

Menjalankan algoritma kalkulasi skor, *Taxonomy Matcher* (Rumpun Ilmu), dan perbandingan keahlian AI terhadap semua kandidat **yang secara eksplisit melamar** pada lowongan tersebut (terdaftar di tabel `apply_jobs`).

### `POST /api/jobs/{job_vacancy_id}/filter`

- **Kapan Digunakan:** Saat HRD menekan tombol "Filter" di halaman detail lowongan pekerjaan.
- **Header:** `X-API-KEY` (Gunakan `API_KEY_FILTERING` dari `.env`)
- **Query Parameter:**
  - `sync` *(boolean, default: true)*: **Wajib `true`** agar sistem langsung menembakkan balik tabel hasil penilaian tanpa perlu hit API lain.
- **Response (200 OK - Sinkron):**
```json
{
  "job_vacancy_id": 45,
  "total_candidates": 100,
  "after_hard_filter": 50,
  "after_taxonomy_filter": 10,
  "duration_seconds": 2.5,
  "candidates": [
    {
      "candidate_id": 123,
      "name": "Budi Santoso",
      "tags": "IT & Software, Python Developer",
      "total_score": 85.0,
      "match_reason": "Kecocokan bidang: sangat sesuai. Skill wajib terpenuhi: Python, FastAPI.",
      "decision": "LAYAK",
      "confidence": "high",
      "score_breakdown": {
         "incomplete_profile": false,
         "skills_match": {"candidate_skills_count": 5}
      }
    }
  ]
}
```

---

## 4. API 4: Mix-Match (Pencarian Talent Pool)

Mirip dengan Filtering, namun algoritma ini secara agresif menyisir **seluruh 100% kandidat aktif di database**, tanpa peduli apakah mereka melamar pada lowongan tersebut atau tidak. Tujuannya adalah mencari bibit unggul tersembunyi.

### `POST /api/jobs/{job_vacancy_id}/mix-match`

- **Kapan Digunakan:** Saat HRD kekurangan pelamar bagus dan menekan tombol "Cari di Database / Mix-Match".
- **Header:** `X-API-KEY` (Gunakan `API_KEY_MIX_MATCH` dari `.env`)
- **Query Parameter:**
  - `sync` *(boolean, default: true)*: Dibiarkan `true` agar *Dashboard* langsung terisi.
- **Response (200 OK - Sinkron):**
*(Format respons JSON persis sama seperti API Filtering di atas, berisi daftar pelamar unggulan beserta alasannya).*

---

## 5. API Pendukung

Dua *endpoint* di bawah ini berguna untuk mengambil data spesifik tanpa perlu menjalankan ulang AI:

1. **Cek Status Ekstraksi Profil:**
   `GET /api/candidates/{user_id}/tags`
   *(Mengecek apakah proses tagger data form pelamar sudah selesai atau belum).*

2. **Lihat Daftar Kandidat Tereliminasi (Gugur):**
   `GET /api/jobs/{job_vacancy_id}/eliminated`
   *(Menampilkan daftar orang yang nilainya jelek/tidak lolos beserta penjelasan 'Mengapa mereka tidak lolos' dalam bahasa Indonesia).*

3. **Lihat Hasil Lolos (Refresh Cache):**
   `GET /api/jobs/{job_vacancy_id}/results`
   *(Digunakan jika HRD sekadar memuat ulang halaman browser keesokan harinya, tanpa perlu me-run AI Filtering lagi dari awal).*
