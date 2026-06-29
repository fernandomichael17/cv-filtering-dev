-- ═══════════════════════════════════════════════════════════════
-- Seed data untuk development lokal
-- Kolom mengikuti skema database aktual (init.sql)
-- ═══════════════════════════════════════════════════════════════

-- Users dummy
INSERT INTO users (name, email, password, role) VALUES
('Andi Pratama', 'andi.pratama@mail.com', 'hashed', 'candidate'),
('Siti Nurhaliza', 'siti.nurhaliza@mail.com', 'hashed', 'candidate'),
('Budi Santoso', 'budi.santoso@mail.com', 'hashed', 'candidate'),
('Dewi Lestari', 'dewi.lestari@mail.com', 'hashed', 'candidate'),
('Rizky Hidayat', 'rizky.hidayat@mail.com', 'hashed', 'candidate'),
('Putri Wulandari', 'putri.wulandari@mail.com', 'hashed', 'candidate'),
('Fajar Rahman', 'fajar.rahman@mail.com', 'hashed', 'candidate'),
('Maya Sari', 'maya.sari@mail.com', 'hashed', 'candidate'),
('Hendra Gunawan', 'hendra.gunawan@mail.com', 'hashed', 'candidate'),
('Lisa Permata', 'lisa.permata@mail.com', 'hashed', 'candidate'),
('Ahmad Fauzi', 'ahmad.fauzi@mail.com', 'hashed', 'candidate'),
('Rina Wijaya', 'rina.wijaya@mail.com', 'hashed', 'candidate'),
('Doni Setiawan', 'doni.setiawan@mail.com', 'hashed', 'candidate'),
('Nadia Amalia', 'nadia.amalia@mail.com', 'hashed', 'candidate'),
('Rudi Hartono', 'rudi.hartono@mail.com', 'hashed', 'candidate'),
('Indah Permatasari', 'indah.permata@mail.com', 'hashed', 'candidate'),
('Yoga Aditya', 'yoga.aditya@mail.com', 'hashed', 'candidate'),
('Kartika Dewi', 'kartika.dewi@mail.com', 'hashed', 'candidate'),
('Bayu Nugroho', 'bayu.nugroho@mail.com', 'hashed', 'candidate'),
('Winda Rahayu', 'winda.rahayu@mail.com', 'hashed', 'candidate'),
('Salsa Nabila', 'salsa.nabila@mail.com', 'hashed', 'candidate'),
('Tono Fresh Grad', 'tono.fg@mail.com', 'hashed', 'candidate');

-- Require (kandidat)
INSERT INTO require (firstname, lastname, gender, dateofbirth, city, gmail, phone, user_id, marital_status, is_fresh_graduate, q15_expected_income, q16_available_from, is_delete) VALUES
('Andi', 'Pratama', 'Laki-laki', '1996-05-15', 'Jakarta', 'andi.pratama@mail.com', '081234567001', 1, 'Belum Menikah', FALSE, 12000000, '2025-02-01', FALSE),
('Siti', 'Nurhaliza', 'Perempuan', '1995-08-20', 'Bandung', 'siti.nurhaliza@mail.com', '081234567002', 2, 'Belum Menikah', FALSE, 15000000, '2025-03-01', FALSE),
('Budi', 'Santoso', 'Laki-laki', '1997-03-10', 'Surabaya', 'budi.santoso@mail.com', '081234567003', 3, 'Belum Menikah', FALSE, 6000000, '2025-01-15', FALSE),
('Dewi', 'Lestari', 'Perempuan', '1994-11-22', 'Yogyakarta', 'dewi.lestari@mail.com', '081234567004', 4, 'Menikah', FALSE, 18000000, '2025-04-01', FALSE),
('Rizky', 'Hidayat', 'Laki-laki', '1996-07-08', 'Jakarta', 'rizky.hidayat@mail.com', '081234567005', 5, 'Belum Menikah', FALSE, 10000000, '2025-02-15', FALSE),
('Putri', 'Wulandari', 'Perempuan', '1999-01-25', 'Semarang', 'putri.wulandari@mail.com', '081234567006', 6, 'Belum Menikah', FALSE, 5000000, NULL, FALSE),
('Fajar', 'Rahman', 'Laki-laki', '1997-09-30', 'Medan', 'fajar.rahman@mail.com', '081234567007', 7, 'Belum Menikah', FALSE, 8000000, '2025-01-01', FALSE),
('Maya', 'Sari', 'Perempuan', '1995-04-18', 'Malang', 'maya.sari@mail.com', '081234567008', 8, 'Belum Menikah', FALSE, 14000000, '2025-03-15', FALSE),
('Hendra', 'Gunawan', 'Laki-laki', '1993-12-05', 'Jakarta', 'hendra.gunawan@mail.com', '081234567009', 9, 'Menikah', FALSE, 20000000, NULL, FALSE),
('Lisa', 'Permata', 'Perempuan', '1997-06-14', 'Tangerang', 'lisa.permata@mail.com', '081234567010', 10, 'Belum Menikah', FALSE, 11000000, '2025-02-01', FALSE),
('Ahmad', 'Fauzi', 'Laki-laki', '1998-02-28', 'Depok', 'ahmad.fauzi@mail.com', '081234567011', 11, 'Belum Menikah', FALSE, 9000000, '2025-01-15', FALSE),
('Rina', 'Wijaya', 'Perempuan', '1995-10-12', 'Bekasi', 'rina.wijaya@mail.com', '081234567012', 12, 'Belum Menikah', FALSE, 13000000, '2025-04-01', FALSE),
('Doni', 'Setiawan', 'Laki-laki', '1996-08-07', 'Bogor', 'doni.setiawan@mail.com', '081234567013', 13, 'Belum Menikah', FALSE, 10000000, '2025-02-01', FALSE),
('Nadia', 'Amalia', 'Perempuan', '1997-01-19', 'Jakarta', 'nadia.amalia@mail.com', '081234567014', 14, 'Belum Menikah', FALSE, 16000000, '2025-03-01', FALSE),
('Rudi', 'Hartono', 'Laki-laki', '1994-07-25', 'Surabaya', 'rudi.hartono@mail.com', '081234567015', 15, 'Menikah', FALSE, 22000000, NULL, FALSE),
('Indah', 'Permatasari', 'Perempuan', '1996-03-11', 'Jakarta', 'indah.permata@mail.com', '081234567016', 16, 'Belum Menikah', FALSE, 18000000, '2025-04-15', FALSE),
('Yoga', 'Aditya', 'Laki-laki', '1998-11-03', 'Bandung', 'yoga.aditya@mail.com', '081234567017', 17, 'Belum Menikah', FALSE, 9000000, '2025-01-15', FALSE),
('Kartika', 'Dewi', 'Perempuan', '1998-05-20', 'Makassar', 'kartika.dewi@mail.com', '081234567018', 18, 'Belum Menikah', FALSE, 8000000, '2025-02-01', FALSE),
('Bayu', 'Nugroho', 'Laki-laki', '1995-09-15', 'Jakarta', 'bayu.nugroho@mail.com', '081234567019', 19, 'Menikah', FALSE, 25000000, NULL, FALSE),
('Winda', 'Rahayu', 'Perempuan', '1997-04-08', 'Yogyakarta', 'winda.rahayu@mail.com', '081234567020', 20, 'Belum Menikah', FALSE, 8000000, '2025-03-01', FALSE),
('Salsa', 'Nabila', 'Perempuan', '2001-12-30', 'Surabaya', 'salsa.nabila@mail.com', '081234567022', 21, 'Belum Menikah', FALSE, 4000000, '2025-01-01', FALSE),
('Tono', 'Mahasiswa', 'Laki-laki', '2001-06-15', 'Jakarta', 'tono.fg@mail.com', '081234567023', 22, 'Belum Menikah', TRUE, 5000000, '2025-07-01', FALSE);

-- Education (education_id: 1=SD, 2=SMP, 3=SMA/SMK, 4=D3, 5=S1, 6=S2, 7=S3)
INSERT INTO requireeducation (requireid, institutionname, major, education_id, score, startyear, endyear) VALUES
(1, 'Universitas Indonesia', 'Teknik Informatika', 5, '3.65', 2015, 2019),
(2, 'Institut Teknologi Bandung', 'Ilmu Komputer', 5, '3.80', 2014, 2018),
(2, 'Institut Teknologi Bandung', 'Ilmu Komputer', 6, '3.90', 2018, 2020),
(3, 'Universitas Airlangga', 'Manajemen', 5, '3.20', 2016, 2020),
(4, 'Universitas Gadjah Mada', 'Akuntansi', 5, '3.55', 2013, 2017),
(5, 'Universitas Bina Nusantara', 'Sistem Informasi', 5, '3.40', 2015, 2019),
(6, 'SMK Negeri 1 Semarang', 'Administrasi Perkantoran', 3, NULL, 2015, 2018),
(7, 'Politeknik Negeri Medan', 'Teknik Komputer', 4, '3.30', 2016, 2019),
(8, 'Universitas Brawijaya', 'Psikologi', 5, '3.50', 2014, 2018),
(9, 'Universitas Trisakti', 'Teknik Elektro', 5, '3.25', 2012, 2016),
(10, 'Universitas Pelita Harapan', 'Teknologi Informasi', 5, '3.45', 2016, 2020),
(11, 'Universitas Gunadarma', 'Teknik Informatika', 5, '3.35', 2017, 2021),
(12, 'Universitas Padjadjaran', 'Ekonomi', 5, '3.40', 2014, 2018),
(13, 'IPB University', 'Teknik Industri', 5, '3.50', 2015, 2019),
(14, 'Universitas Atmajaya', 'Ilmu Komputer', 5, '3.60', 2016, 2020),
(15, 'ITS Surabaya', 'Teknik Elektro', 5, '3.55', 2013, 2017),
(15, 'ITS Surabaya', 'Teknik Elektro', 6, '3.70', 2017, 2019),
(16, 'Universitas Indonesia', 'Administrasi Bisnis', 5, '3.45', 2015, 2019),
(17, 'Telkom University', 'Rekayasa Perangkat Lunak', 5, '3.50', 2017, 2021),
(18, 'Universitas Hasanuddin', 'Perpajakan', 4, '3.30', 2017, 2020),
(19, 'Universitas Binus', 'Computer Science', 5, '3.60', 2014, 2018),
(20, 'UPN Veteran Yogyakarta', 'Teknik Industri', 5, '3.40', 2016, 2020),
(21, 'SMA Negeri 5 Surabaya', 'IPA', 3, NULL, 2017, 2020),
(22, 'Universitas Indonesia', 'Teknik Informatika', 5, '3.50', 2019, 2023);

-- Work Experience
INSERT INTO requireworkexperience (requireid, companyname, joblevel, jobdesk, startyear, endyear, startdate, enddate, iscurrent) VALUES
(1, 'PT Tokopedia', 'Backend Developer', 'Backend developer menggunakan Go dan PostgreSQL. Membangun microservices untuk payment gateway.', 2019, 2022, '2019-07-01', '2022-07-01', FALSE),
(1, 'PT Bukalapak', 'Junior Developer', 'Junior developer, membantu development fitur katalog produk menggunakan Python Django.', 2022, NULL, '2022-08-01', NULL, TRUE),
(2, 'PT Gojek', 'Data Engineer', 'Data engineer, membangun ETL pipeline menggunakan Apache Spark dan Airflow. Mengelola data warehouse di BigQuery.', 2020, NULL, '2020-06-01', NULL, TRUE),
(3, 'PT Bank BCA', 'Staff Administrasi', 'Staff administrasi dan pengelolaan dokumen nasabah. Input data dan pembuatan laporan bulanan.', 2020, 2022, '2020-07-01', '2022-07-01', FALSE),
(4, 'KPMG Indonesia', 'External Auditor', 'External auditor, melakukan audit laporan keuangan perusahaan multinasional. Menyusun working paper dan audit report.', 2017, 2021, '2017-08-01', '2021-08-01', FALSE),
(4, 'PT Unilever', 'Internal Auditor', 'Internal auditor, memastikan kepatuhan SOP dan melakukan risk assessment.', 2021, NULL, '2021-09-01', NULL, TRUE),
(5, 'PT Shopee', 'Full Stack Developer', 'Full-stack developer, membangun fitur marketplace menggunakan React dan Node.js. Mengintegrasikan payment API.', 2019, 2022, '2019-08-01', '2022-02-01', FALSE),
(5, 'Freelance', 'Web Developer', 'Membuat website e-commerce untuk UMKM menggunakan WordPress dan WooCommerce.', 2022, 2023, '2022-03-01', '2023-03-01', FALSE),
(6, 'PT Indofood', 'Staff Administrasi Gudang', 'Staff administrasi gudang, mengelola stok dan pencatatan keluar masuk barang.', 2018, 2021, '2018-07-01', '2021-07-01', FALSE),
(7, 'PT Telkom Indonesia', 'IT Support', 'IT support dan maintenance jaringan LAN/WAN. Troubleshooting hardware dan software.', 2019, NULL, '2019-06-01', NULL, TRUE),
(8, 'PT Astra International', 'HR Recruitment Specialist', 'HR recruitment specialist, melakukan screening CV, interview, dan onboarding karyawan baru.', 2018, 2021, '2018-07-01', '2021-07-01', FALSE),
(8, 'PT Pertamina', 'HR Development', 'HR development, merancang program training dan pengembangan karyawan.', 2021, NULL, '2021-08-01', NULL, TRUE),
(9, 'PT PLN', 'Engineer Pembangkit', 'Engineer pembangkit listrik, supervisi maintenance turbin dan generator.', 2016, 2021, '2016-08-01', '2021-08-01', FALSE),
(9, 'PT Schneider Electric', 'Sales Engineer', 'Sales engineer, konsultasi solusi kelistrikan untuk industri manufaktur.', 2021, NULL, '2021-09-01', NULL, TRUE),
(10, 'PT Traveloka', 'Mobile Developer iOS', 'Mobile developer iOS, membangun fitur booking hotel dan flight menggunakan Swift. Implementasi push notification dan deep linking.', 2020, 2022, '2020-07-01', '2022-07-01', FALSE),
(11, 'PT Ruangguru', 'Frontend Developer', 'Frontend developer, membangun dashboard analytics menggunakan Vue.js dan Chart.js.', 2021, NULL, '2021-08-01', NULL, TRUE),
(12, 'PT Tokopedia', 'Business Analyst', 'Business analyst, menganalisis metrik pertumbuhan user dan revenue. Membuat dashboard reporting di Metabase.', 2018, 2021, '2018-07-01', '2021-01-01', FALSE),
(12, 'PT Dana Indonesia', 'Product Analyst', 'Product analyst, melakukan A/B testing dan user behavior analysis.', 2021, NULL, '2021-02-01', NULL, TRUE),
(13, 'PT Toyota Astra Motor', 'Production Planning', 'Production planning, mengelola jadwal produksi dan supply chain. Implementasi lean manufacturing.', 2019, 2022, '2019-07-01', '2022-07-01', FALSE),
(14, 'PT Tiket.com', 'DevOps Engineer', 'DevOps engineer, mengelola CI/CD pipeline menggunakan Jenkins dan Docker. Deployment ke AWS ECS dan monitoring dengan Datadog.', 2020, 2022, '2020-07-01', '2022-07-01', FALSE),
(14, 'PT OVO', 'Backend Developer', 'Backend developer, membangun API microservices menggunakan Java Spring Boot.', 2022, NULL, '2022-08-01', NULL, TRUE),
(15, 'PT Siemens Indonesia', 'Automation Engineer', 'Automation engineer, programming PLC dan SCADA untuk pabrik manufaktur.', 2019, NULL, '2019-07-01', NULL, TRUE),
(16, 'PT McKinsey & Company', 'Management Consultant', 'Management consultant, membantu transformasi digital perusahaan BUMN. Analisis strategi dan roadmap teknologi.', 2019, 2022, '2019-08-01', '2022-08-01', FALSE),
(17, 'PT Blibli', 'QA Engineer', 'QA engineer, automation testing menggunakan Selenium dan Cypress. Membangun test framework untuk API testing.', 2021, NULL, '2021-08-01', NULL, TRUE),
(18, 'KAP PwC Indonesia', 'Tax Consultant', 'Tax consultant, membantu pelaporan pajak PPh Badan dan PPN untuk klien korporat.', 2020, NULL, '2020-06-01', NULL, TRUE),
(19, 'PT Grab Indonesia', 'Senior Backend Developer', 'Senior backend developer, membangun real-time location service menggunakan Go dan Redis. Optimasi database query untuk high-throughput system.', 2018, 2022, '2018-07-01', '2021-07-01', FALSE),
(19, 'PT Bukalapak', 'Backend Developer', 'Backend developer, membangun REST API untuk fitur marketplace menggunakan Ruby on Rails.', 2021, NULL, '2021-08-01', NULL, TRUE),
(20, 'PT Astra Honda Motor', 'Quality Control Engineer', 'Quality control engineer, inspeksi kualitas produk di lini produksi. Analisis defect rate dan root cause analysis.', 2020, 2022, '2020-07-01', '2022-07-01', FALSE),
(21, 'Toko Online Mandiri', 'Admin Online Shop', 'Admin online shop, mengelola pesanan dan customer service via WhatsApp dan Shopee.', 2020, 2022, '2020-06-01', '2021-12-01', FALSE);
-- Kandidat 22 (Tono Fresh Grad) tidak punya pengalaman kerja

-- Training
INSERT INTO requiretraining (requireid, trainingname, certificateno, startyear, endyear) VALUES
(1, 'AWS Certified Developer', 'AWS-DEV-001', 2021, 2021),
(2, 'Google Cloud Professional Data Engineer', 'GCP-DE-002', 2020, 2020),
(2, 'Apache Spark Fundamentals', 'SPARK-003', 2019, 2019),
(4, 'Certified Public Accountant (CPA)', 'CPA-2021-004', 2021, 2021),
(5, 'Meta Front-End Developer Certificate', 'META-FE-005', 2022, 2022),
(7, 'CompTIA A+', 'COMPTIA-A-007', 2020, 2020),
(7, 'CCNA Routing and Switching', 'CCNA-RS-007', 2021, 2021),
(8, 'BNSP Certified HR Professional', 'BNSP-HRP-008', 2020, 2020),
(9, 'Certified Energy Manager', 'CEM-009', 2019, 2019),
(10, 'Apple Certified iOS Developer', 'APPLE-IOS-010', 2021, 2021),
(12, 'Google Data Analytics Certificate', 'GDA-012', 2020, 2020),
(13, 'Six Sigma Green Belt', 'SSGB-013', 2021, 2021),
(14, 'AWS Solutions Architect Associate', 'AWS-SAA-014', 2021, 2021),
(14, 'Kubernetes Administrator (CKA)', 'CKA-014', 2022, 2022),
(15, 'Siemens Certified PLC Programmer', 'SIEMENS-PLC-015', 2020, 2020),
(16, 'Project Management Professional (PMP)', 'PMP-016', 2021, 2021),
(17, 'ISTQB Certified Tester', 'ISTQB-017', 2022, 2022),
(18, 'Brevet Pajak A & B', 'BREVET-AB-018', 2020, 2020),
(20, 'ISO 9001:2015 Internal Auditor', 'ISO-IA-020', 2021, 2021);

-- Job Vacancy (contoh lowongan)
INSERT INTO job_vacancy (job_vacancy_name, job_vacancy_job_desc, job_vacancy_job_spec) VALUES
('Backend Developer', '<p>Kami mencari Backend Developer untuk bergabung dengan tim teknologi.</p><ul><li>Membangun dan memelihara REST API</li><li>Mengoptimasi performa database</li><li>Berkolaborasi dengan tim frontend</li></ul>', '<p>Persyaratan:</p><ul><li>Pendidikan minimal S1 Teknik Informatika/Ilmu Komputer</li><li>Pengalaman minimal 2 tahun sebagai backend developer</li><li>Menguasai Python atau Go</li><li>Familiar dengan PostgreSQL</li><li>Diutamakan memiliki pengalaman dengan Docker dan AWS</li><li>Usia maksimal 35 tahun</li></ul>'),
('Staff Akuntansi', '<p>Dibutuhkan Staff Akuntansi untuk mengelola pembukuan dan laporan keuangan.</p><ul><li>Membuat jurnal dan laporan keuangan bulanan</li><li>Rekonsiliasi bank</li><li>Mengelola pajak PPh dan PPN</li></ul>', '<p>Persyaratan:</p><ul><li>Pendidikan minimal D3 Akuntansi/Perpajakan</li><li>Fresh graduate dipersilakan, pengalaman 1-2 tahun diutamakan</li><li>Menguasai Ms. Excel dan software akuntansi</li><li>Memiliki Brevet A&B menjadi nilai tambah</li><li>Belum menikah</li></ul>'),
('Management Trainee', '<p>Program pengembangan karir untuk lulusan baru yang berpotensi menjadi pemimpin masa depan.</p><ul><li>Rotasi di berbagai departemen</li><li>Mentoring oleh senior management</li><li>Project assignment</li></ul>', '<p>Persyaratan:</p><ul><li>Pendidikan minimal S1 semua jurusan</li><li>Fresh graduate atau maksimal 1 tahun pengalaman</li><li>IPK minimal 3.0</li><li>Usia maksimal 25 tahun</li><li>Bersedia ditempatkan di seluruh Indonesia</li><li>Belum menikah</li></ul>');

-- Apply Jobs (kandidat yang melamar)
INSERT INTO apply_jobs (job_vacancy_id, user_id) VALUES
-- Backend Developer: 7 pelamar
(1, 1), (1, 2), (1, 5), (1, 7), (1, 10), (1, 11), (1, 14),
-- Staff Akuntansi: 5 pelamar
(2, 3), (2, 4), (2, 12), (2, 18), (2, 22),
-- Management Trainee: 6 pelamar
(3, 3), (3, 6), (3, 11), (3, 21), (3, 22), (3, 17);
