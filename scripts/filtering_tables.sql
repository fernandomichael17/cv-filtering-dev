-- ==============================================================================
-- DATABASE SCRIPT UNTUK MICROSERVICE CV-FILTERING
-- Keterangan: Script ini hanya berisi pembuatan tabel read-write baru.
-- Relasi Foreign Key sengaja dirancang CASCADE terhadap tabel eksisting 
-- (require, requireworkexperience, job_vacancy) agar pembersihan data 
-- terotomatisasi jika data induk di web karir dihapus.
-- ==============================================================================

-- 1. Tabel Tag Kandidat Keseluruhan
CREATE TABLE IF NOT EXISTS candidate_tags (
    id SERIAL PRIMARY KEY,
    require_id INTEGER UNIQUE NOT NULL REFERENCES require(requireid) ON DELETE CASCADE,
    tags TEXT,
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW()
);

-- 2. Tabel Tag Pengalaman Kerja Spesifik
CREATE TABLE IF NOT EXISTS candidate_experience_tags (
    id SERIAL PRIMARY KEY,
    work_id INTEGER UNIQUE NOT NULL REFERENCES requireworkexperience(workid) ON DELETE CASCADE,
    field_tag VARCHAR(100),
    role_tag VARCHAR(100),
    tags TEXT,
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW()
);

-- 3. Tabel Keahlian Kandidat (Hard Skill, Soft Skill, Language)
CREATE TABLE IF NOT EXISTS candidate_skills (
    id SERIAL PRIMARY KEY,
    require_id INTEGER UNIQUE NOT NULL REFERENCES require(requireid) ON DELETE CASCADE,
    hard_skill TEXT,
    soft_skill TEXT,
    language TEXT,
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW()
);

-- 4. Tabel Cache Parsing Lowongan Kerja (Job Vacancy)
CREATE TABLE IF NOT EXISTS parsed_job_cache (
    id SERIAL PRIMARY KEY,
    job_vacancy_id INTEGER UNIQUE NOT NULL,
    job_vacancy_name VARCHAR(255),
    parsed_requirements JSONB,
    tags JSONB,
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW()
);

-- 5. Tabel Hasil Filtering & Mix-Match (Score Breakdown)
CREATE TABLE IF NOT EXISTS filtering_results (
    id SERIAL PRIMARY KEY,
    job_vacancy_id INTEGER NOT NULL REFERENCES job_vacancy(job_vacancy_id) ON DELETE CASCADE,
    require_id INTEGER NOT NULL REFERENCES require(requireid) ON DELETE CASCADE,
    candidate_name VARCHAR(255),
    stage VARCHAR(50) NOT NULL,
    decision VARCHAR(50) NOT NULL,
    reason TEXT,
    similarity_score FLOAT,
    total_score FLOAT,
    confidence VARCHAR(50),
    score_breakdown JSONB,
    created_at TIMESTAMP DEFAULT NOW()
);
