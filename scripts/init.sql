-- ═══════════════════════════════════════════════════════════════
-- Tabel READ-ONLY (milik web karir, diklon untuk development)
-- ═══════════════════════════════════════════════════════════════

CREATE TABLE IF NOT EXISTS users (
    id SERIAL PRIMARY KEY,
    name VARCHAR(255),
    email VARCHAR(255) UNIQUE,
    email_verified_at TIMESTAMP,
    password VARCHAR(255),
    remember_token VARCHAR(255),
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW(),
    accepted_terms_at TIMESTAMP,
    date_of_birth TIMESTAMP,
    role VARCHAR(50),
    location_id INTEGER,
    is_delete BOOLEAN DEFAULT FALSE,
    account_deleted_at TIMESTAMP
);

CREATE TABLE IF NOT EXISTS require (
    requireid SERIAL PRIMARY KEY,
    firstname VARCHAR(255),
    middlename VARCHAR(255),
    lastname VARCHAR(255),
    gender VARCHAR(20),
    dateofbirth VARCHAR(50),
    cvpath VARCHAR(500),
    photopath VARCHAR(500),
    idcardpath VARCHAR(500),
    address TEXT,
    city VARCHAR(255),
    gmail VARCHAR(255),
    linkedin VARCHAR(255),
    instagram VARCHAR(255),
    phone VARCHAR(50),
    createdat TIMESTAMP DEFAULT NOW(),
    updatedat TIMESTAMP DEFAULT NOW(),
    admin_notes TEXT,
    status_updated_at TIMESTAMP,
    reviewed_by INTEGER,
    user_id INTEGER REFERENCES users(id),
    marital_status VARCHAR(50),
    is_fresh_graduate BOOLEAN DEFAULT FALSE,
    ref1_name VARCHAR(255),
    ref1_address_phone VARCHAR(500),
    ref1_occupation VARCHAR(255),
    ref1_relationship VARCHAR(100),
    ref2_name VARCHAR(255),
    ref2_address_phone VARCHAR(500),
    ref2_occupation VARCHAR(255),
    ref2_relationship VARCHAR(100),
    ref3_name VARCHAR(255),
    ref3_address_phone VARCHAR(500),
    ref3_occupation VARCHAR(255),
    ref3_relationship VARCHAR(100),
    emergency1_name VARCHAR(255),
    emergency1_address TEXT,
    emergency1_phone VARCHAR(50),
    emergency1_relationship VARCHAR(100),
    emergency2_name VARCHAR(255),
    emergency2_address TEXT,
    emergency2_phone VARCHAR(50),
    emergency2_relationship VARCHAR(100),
    q11_willing_outside_jakarta BOOLEAN,
    q14_current_income INTEGER,
    q15_expected_income INTEGER,
    q16_available_from VARCHAR(100),
    is_delete BOOLEAN DEFAULT FALSE
);

CREATE TABLE IF NOT EXISTS requireeducation (
    eduid SERIAL PRIMARY KEY,
    requireid INTEGER REFERENCES require(requireid),
    institutionname VARCHAR(500),
    major VARCHAR(255),
    startdate TIMESTAMP,
    enddate TIMESTAMP,
    year INTEGER,
    score VARCHAR(20),
    education_id INTEGER,
    startyear INTEGER,
    endyear INTEGER
);

CREATE TABLE IF NOT EXISTS requireworkexperience (
    workid SERIAL PRIMARY KEY,
    requireid INTEGER REFERENCES require(requireid),
    companyname VARCHAR(500),
    joblevel VARCHAR(255),
    startdate TIMESTAMP,
    enddate TIMESTAMP,
    salary VARCHAR(50),
    iscurrent BOOLEAN DEFAULT FALSE,
    eexp_comments TEXT,
    jobdesk TEXT,
    startyear INTEGER,
    endyear INTEGER
);

CREATE TABLE IF NOT EXISTS requiretraining (
    trainingid SERIAL PRIMARY KEY,
    requireid INTEGER REFERENCES require(requireid),
    trainingname VARCHAR(500),
    certificateno VARCHAR(255),
    starttrainingdate TIMESTAMP,
    endtrainingdate TIMESTAMP,
    startyear INTEGER,
    endyear INTEGER
);

-- Tabel job_vacancy (PLACEHOLDER — struktur aktual menunggu konfirmasi)
CREATE TABLE IF NOT EXISTS job_vacancy (
    job_vacancy_id SERIAL PRIMARY KEY,
    job_vacancy_name VARCHAR(255),
    job_vacancy_job_desc TEXT,
    job_vacancy_job_spec TEXT,
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW()
);

-- Tabel apply_jobs (PLACEHOLDER — struktur aktual menunggu konfirmasi)
CREATE TABLE IF NOT EXISTS apply_jobs (
    id SERIAL PRIMARY KEY,
    job_vacancy_id INTEGER REFERENCES job_vacancy(job_vacancy_id),
    user_id INTEGER REFERENCES users(id),
    created_at TIMESTAMP DEFAULT NOW()
);


-- ═══════════════════════════════════════════════════════════════
-- Tabel READ-WRITE (milik CV-Filtering)
-- ═══════════════════════════════════════════════════════════════

-- Pengganti tags_cv
CREATE TABLE IF NOT EXISTS candidate_tags (
    id SERIAL PRIMARY KEY,
    require_id INTEGER UNIQUE NOT NULL REFERENCES require(requireid) ON DELETE CASCADE,
    tags TEXT,
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW()
);

-- Pengganti tags_jobs (per pengalaman kerja)
CREATE TABLE IF NOT EXISTS candidate_experience_tags (
    id SERIAL PRIMARY KEY,
    work_id INTEGER UNIQUE NOT NULL REFERENCES requireworkexperience(workid) ON DELETE CASCADE,
    field_tag VARCHAR(100),
    role_tag VARCHAR(100),
    tags TEXT,
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW()
);

-- Pengganti require_skills
CREATE TABLE IF NOT EXISTS candidate_skills (
    id SERIAL PRIMARY KEY,
    require_id INTEGER UNIQUE NOT NULL REFERENCES require(requireid) ON DELETE CASCADE,
    hard_skill TEXT,
    soft_skill TEXT,
    language TEXT,
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW()
);

-- Cache hasil parsing LLM untuk job_vacancy
CREATE TABLE IF NOT EXISTS parsed_job_cache (
    id SERIAL PRIMARY KEY,
    job_vacancy_id INTEGER UNIQUE NOT NULL,
    job_vacancy_name VARCHAR(255),
    parsed_requirements JSONB,
    tags JSONB,
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW()
);

-- Hasil filtering (Penyesuaian kolom dan foreign key)
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

