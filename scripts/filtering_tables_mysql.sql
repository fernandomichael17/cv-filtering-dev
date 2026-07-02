-- ==============================================================================
-- DATABASE SCRIPT UNTUK MICROSERVICE CV-FILTERING (VERSI MYSQL)
-- Keterangan: Script ini hanya berisi pembuatan tabel read-write baru.
-- Relasi Foreign Key sengaja dirancang CASCADE terhadap tabel eksisting 
-- (require, requireworkexperience, job_vacancy) agar pembersihan data 
-- terotomatisasi jika data induk di web karir dihapus.
-- ==============================================================================

-- 1. Tabel Tag Kandidat Keseluruhan
CREATE TABLE IF NOT EXISTS candidate_tags (
    id INT AUTO_INCREMENT PRIMARY KEY,
    require_id INT NOT NULL UNIQUE,
    tags TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    FOREIGN KEY (require_id) REFERENCES require(requireid) ON DELETE CASCADE
);

-- 2. Tabel Tag Pengalaman Kerja Spesifik
CREATE TABLE IF NOT EXISTS candidate_experience_tags (
    id INT AUTO_INCREMENT PRIMARY KEY,
    work_id INT NOT NULL UNIQUE,
    field_tag VARCHAR(100),
    role_tag VARCHAR(100),
    tags TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    FOREIGN KEY (work_id) REFERENCES requireworkexperience(workid) ON DELETE CASCADE
);

-- 3. Tabel Keahlian Kandidat (Hard Skill, Soft Skill, Language)
CREATE TABLE IF NOT EXISTS candidate_skills (
    id INT AUTO_INCREMENT PRIMARY KEY,
    require_id INT NOT NULL UNIQUE,
    hard_skill TEXT,
    soft_skill TEXT,
    language TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    FOREIGN KEY (require_id) REFERENCES require(requireid) ON DELETE CASCADE
);

-- 4. Tabel Cache Parsing Lowongan Kerja (Job Vacancy)
CREATE TABLE IF NOT EXISTS parsed_job_cache (
    id INT AUTO_INCREMENT PRIMARY KEY,
    job_vacancy_id INT NOT NULL UNIQUE,
    job_vacancy_name VARCHAR(255),
    parsed_requirements JSON,
    tags JSON,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP
);

-- 5. Tabel Hasil Filtering & Mix-Match (Score Breakdown)
CREATE TABLE IF NOT EXISTS filtering_results (
    id INT AUTO_INCREMENT PRIMARY KEY,
    job_vacancy_id INT NOT NULL,
    require_id INT NOT NULL,
    candidate_name VARCHAR(255),
    stage VARCHAR(50) NOT NULL,
    decision VARCHAR(50) NOT NULL,
    reason TEXT,
    similarity_score FLOAT,
    total_score FLOAT,
    confidence VARCHAR(50),
    score_breakdown JSON,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (job_vacancy_id) REFERENCES job_vacancy(job_vacancy_id) ON DELETE CASCADE,
    FOREIGN KEY (require_id) REFERENCES require(requireid) ON DELETE CASCADE
);
