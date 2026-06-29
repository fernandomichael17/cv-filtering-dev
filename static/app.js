/**
 * @fileoverview Logika utama SPA (Single Page Application) untuk Dashboard & Simulator CV Filtering.
 * Mengontrol autentikasi simulasi, registrasi, render diagram ERD, funnel chart, dan interaksi API.
 */

// State Global Aplikasi
let currentView = 'login';
let currentRole = 'hrd'; // 'hrd' atau 'candidate'
let loggedCandidateId = null; // requireid kandidat yang masuk
let loggedUserId = null; // user_id kandidat yang masuk
let activeJobId = null;

// Daftar konstanta default API Keys untuk development
const DEFAULT_KEYS = {
    job: 'd22bc7171f3c4e78213e436cb31342f7c1b00a6636257f69271ee86626a67823',
    extract: 'b99d79174d95d023a93ef28d46be858625dea8172194e3c9bb601202bd4533e8',
    filter: 'a93a0c99e991eef96cc4a0ac83e0036ff3732310e7187330eaca970682ea6200',
    mix: '88c08638fdefee320853b583b3d9d597395ae3ed74611b7a4458acfcdf309ac9'
};

// ═══════════════════════════════════════════════════════════════
// INISIALISASI & VIEW ROUTER
// ═══════════════════════════════════════════════════════════════

document.addEventListener('DOMContentLoaded', () => {
    initApp();
});


/**
 * Menginisialisasi aplikasi pada startup.
 */
function initApp() {
    loadSavedApiKeys();
    loadCandidatesDropdown();
    // Secara default, set tab HRD & Candidate yang aktif
    switchHrdTab('overview');
    switchCandTab('resume');
}


/**
 * Membuka view tertentu dan menutup view lainnya.
 * 
 * @param {string} viewId - ID dari kontainer view (contoh: 'login-view').
 */
function showView(viewId) {
    document.querySelectorAll('.view').forEach(v => {
        v.classList.remove('active');
    });
    const target = document.getElementById(viewId);
    if (target) {
        target.classList.add('active');
    }
}


/**
 * Mengubah role pada formulir login.
 * 
 * @param {string} role - 'hrd' atau 'candidate'.
 */
function switchLoginRole(role) {
    document.getElementById('btn-select-hrd').classList.toggle('active', role === 'hrd');
    document.getElementById('btn-select-candidate').classList.toggle('active', role === 'candidate');
    
    document.getElementById('form-hrd-login').classList.toggle('active', role === 'hrd');
    document.getElementById('form-candidate-login').classList.toggle('active', role === 'candidate');
}


/**
 * Mengarahkan ke halaman registrasi kandidat baru.
 */
function showRegisterPage() {
    showView('register-view');
}


/**
 * Mengarahkan kembali ke halaman login.
 */
function goToLogin() {
    showView('login-view');
    loadCandidatesDropdown();
}


/**
 * Melakukan logout pengguna dan kembali ke login screen.
 */
function handleLogout() {
    loggedCandidateId = null;
    loggedUserId = null;
    showView('login-view');
    loadCandidatesDropdown();
}

// ═══════════════════════════════════════════════════════════════
// DYNAMIC DROPDOWNS & LOCAL STORAGE API KEYS
// ═══════════════════════════════════════════════════════════════

/**
 * Mengambil daftar kandidat dari SQLite dan mengisi dropdown login.
 */
async function loadCandidatesDropdown() {
    const dropdown = document.getElementById('cand-select');
    if (!dropdown) return;
    
    dropdown.innerHTML = '<option value="">Memuat kandidat...</option>';
    
    try {
        const res = await fetch('/api/portal/candidates');
        if (!res.ok) throw new Error("Gagal mengambil data kandidat");
        
        const data = await res.json();
        renderCandidateOptions(dropdown, data);
    } catch (err) {
        dropdown.innerHTML = '<option value="">Gagal memuat data</option>';
        loggerError("Dropdown kandidat", err);
    }
}


/**
 * Merender daftar opsi kandidat pada dropdown login.
 * 
 * @param {HTMLElement} dropdown - Elemen select dropdown.
 * @param {Array} list - Daftar objek kandidat.
 */
function renderCandidateOptions(dropdown, list) {
    if (list.length === 0) {
        dropdown.innerHTML = '<option value="">Tidak ada kandidat terdaftar</option>';
        return;
    }
    
    dropdown.innerHTML = list.map(c => 
        `<option value="${c.requireid}" data-userid="${c.user_id}" data-email="${c.gmail}">
            ${c.firstname} ${c.lastname || ''} (${c.gmail})
         </option>`
    ).join('');
}


/**
 * Memuat API keys yang tersimpan di localStorage.
 */
function loadSavedApiKeys() {
    document.getElementById('key-job').value = localStorage.getItem('API_KEY_JOB') || '';
    document.getElementById('key-extract').value = localStorage.getItem('API_KEY_EXTRACT') || '';
    document.getElementById('key-filter').value = localStorage.getItem('API_KEY_FILTER') || '';
    document.getElementById('key-mix').value = localStorage.getItem('API_KEY_MIX') || '';
}


/**
 * Menyimpan API keys dari form input ke localStorage.
 * 
 * @param {Event} e - Form submit event.
 */
function saveApiKeys(e) {
    e.preventDefault();
    localStorage.setItem('API_KEY_JOB', document.getElementById('key-job').value.trim());
    localStorage.setItem('API_KEY_EXTRACT', document.getElementById('key-extract').value.trim());
    localStorage.setItem('API_KEY_FILTER', document.getElementById('key-filter').value.trim());
    localStorage.setItem('API_KEY_MIX', document.getElementById('key-mix').value.trim());
    alert('API Keys sukses disimpan di browser!');
}


/**
 * Memuat API keys bawaan development (.env) ke input.
 */
function loadDefaultKeys() {
    document.getElementById('key-job').value = DEFAULT_KEYS.job;
    document.getElementById('key-extract').value = DEFAULT_KEYS.extract;
    document.getElementById('key-filter').value = DEFAULT_KEYS.filter;
    document.getElementById('key-mix').value = DEFAULT_KEYS.mix;
}


/**
 * Mendapatkan API Key tertentu berdasarkan tipe modul.
 * 
 * @param {string} type - 'job', 'extract', 'filter', atau 'mix'.
 * @return {string} Kunci API perlindungan rute.
 */
function getApiKey(type) {
    const key = localStorage.getItem('API_KEY_' + type.toUpperCase());
    return key || DEFAULT_KEYS[type] || '';
}

// ═══════════════════════════════════════════════════════════════
// AUTENTIKASI SIMULATOR
// ═══════════════════════════════════════════════════════════════

/**
 * Menangani login portal HRD.
 */
function handleLoginHRD(e) {
    e.preventDefault();
    const email = document.getElementById('hrd-email').value;
    const pass = document.getElementById('hrd-password').value;
    
    if (email === 'hrd@company.com' && pass === 'hrd123') {
        showView('hrd-view');
        loadHrdJobsDropdown();
        loadErdSchema();
        return;
    }
    alert('Kredensial login HRD salah!');
}


/**
 * Menangani login portal Kandidat.
 */
function handleLoginCandidate(e) {
    e.preventDefault();
    const select = document.getElementById('cand-select');
    if (!select || select.value === '') {
        alert('Pilih kandidat terlebih dahulu!');
        return;
    }
    
    const option = select.options[select.selectedIndex];
    loggedCandidateId = parseInt(select.value);
    loggedUserId = parseInt(option.getAttribute('data-userid'));
    
    showView('candidate-view');
    loadCandidateProfile();
    loadCandidateJobsDropdown();
    loadCandidateApplications();
}

// ═══════════════════════════════════════════════════════════════
// WIZARD REGISTRASI KANDIDAT (FORM DYNAMIC FIELD)
// ═══════════════════════════════════════════════════════════════

/**
 * Menambahkan baris isian pendidikan baru di form registrasi.
 */
function addEducationField() {
    const container = document.getElementById('education-list-container');
    const div = document.createElement('div');
    div.className = 'education-item nested-form-item';
    div.innerHTML = `
        <button type="button" class="btn-close-modal" style="position:absolute; right:10px; top:10px;" onclick="this.parentNode.remove()">&times;</button>
        <div class="grid grid-2">
            <div class="form-group">
                <label>Nama Institusi / Universitas</label>
                <input type="text" class="edu-inst" required placeholder="Universitas Indonesia">
            </div>
            <div class="form-group">
                <label>Jurusan</label>
                <input type="text" class="edu-major" required placeholder="Teknik Informatika">
            </div>
        </div>
        <div class="grid grid-4">
            <div class="form-group">
                <label>Tahun Lulus</label>
                <input type="number" class="edu-year" required value="2024">
            </div>
            <div class="form-group">
                <label>IPK / Nilai</label>
                <input type="number" step="0.01" class="edu-score" required value="3.50">
            </div>
            <div class="form-group">
                <label>Tahun Mulai</label>
                <input type="number" class="edu-startyear" required value="2020">
            </div>
            <div class="form-group">
                <label>Tahun Akhir</label>
                <input type="number" class="edu-endyear" required value="2024">
            </div>
        </div>
    `;
    container.appendChild(div);
}


/**
 * Menambahkan baris isian sertifikasi baru di form registrasi.
 */
function addTrainingField() {
    const container = document.getElementById('training-list-container');
    const div = document.createElement('div');
    div.className = 'training-item nested-form-item';
    div.innerHTML = `
        <button type="button" class="btn-close-modal" style="position:absolute; right:10px; top:10px;" onclick="this.parentNode.remove()">&times;</button>
        <div class="grid grid-2">
            <div class="form-group">
                <label>Nama Pelatihan / Sertifikasi</label>
                <input type="text" class="train-name" placeholder="React Developer Certification">
            </div>
            <div class="form-group">
                <label>Nomor Sertifikat</label>
                <input type="text" class="train-cert" placeholder="CERT-12345">
            </div>
        </div>
        <div class="grid grid-2">
            <div class="form-group">
                <label>Tahun Mulai</label>
                <input type="number" class="train-start" value="2024">
            </div>
            <div class="form-group">
                <label>Tahun Selesai</label>
                <input type="number" class="train-end" value="2024">
            </div>
        </div>
    `;
    container.appendChild(div);
}


/**
 * Menambahkan baris isian pengalaman baru di form registrasi.
 */
function addExperienceField() {
    const container = document.getElementById('experience-list-container');
    const div = document.createElement('div');
    div.className = 'experience-item nested-form-item';
    div.innerHTML = `
        <button type="button" class="btn-close-modal" style="position:absolute; right:10px; top:10px;" onclick="this.parentNode.remove()">&times;</button>
        <div class="grid grid-2">
            <div class="form-group">
                <label>Nama Perusahaan</label>
                <input type="text" class="exp-company" placeholder="PT Teknologi Nusantara">
            </div>
            <div class="form-group">
                <label>Posisi / Level Jabatan</label>
                <input type="text" class="exp-level" placeholder="Backend Engineer">
            </div>
        </div>
        <div class="form-group">
            <label>Deskripsi Pekerjaan / Jobdesk</label>
            <textarea class="exp-jobdesk" rows="3" placeholder="Membangun API..."></textarea>
        </div>
        <div class="grid grid-4">
            <div class="form-group">
                <label>Gaji Bulanan (IDR)</label>
                <input type="number" class="exp-salary" value="0">
            </div>
            <div class="form-group">
                <label>Pekerjaan Saat Ini?</label>
                <select class="exp-current">
                    <option value="false">Tidak</option>
                    <option value="true">Ya</option>
                </select>
            </div>
            <div class="form-group">
                <label>Tahun Mulai</label>
                <input type="number" class="exp-startyear" value="2023">
            </div>
            <div class="form-group">
                <label>Tahun Selesai</label>
                <input type="number" class="exp-endyear" value="2024">
            </div>
        </div>
    `;
    container.appendChild(div);
}


/**
 * Mengirim formulir pendaftaran kandidat baru ke API.
 */
async function handleRegisterSubmit(e) {
    e.preventDefault();
    
    const payload = collectRegistrationData();
    
    try {
        const res = await fetch('/api/portal/candidates', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify(payload)
        });
        
        if (!res.ok) {
            const errJson = await res.json();
            throw new Error(errJson.detail || "Registrasi gagal");
        }
        
        alert('Kandidat berhasil didaftarkan ke SQLite & PG!');
        goToLogin();
    } catch (err) {
        alert('Error registrasi: ' + err.message);
        loggerError("Submit registrasi", err);
    }
}


/**
 * Mengumpulkan data dari form registrasi menjadi payload API.
 * 
 * @return {Object} Payload pendaftaran kandidat.
 */
function collectRegistrationData() {
    const payload = {
        name: document.getElementById('reg-name').value.trim(),
        email: document.getElementById('reg-email').value.trim(),
        password: document.getElementById('reg-password').value,
        phone: document.getElementById('reg-phone').value.trim(),
        gender: document.getElementById('reg-gender').value,
        dob: document.getElementById('reg-dob').value,
        city: document.getElementById('reg-city').value.trim(),
        address: document.getElementById('reg-address').value.trim(),
        linkedin: document.getElementById('reg-linkedin').value.trim(),
        instagram: document.getElementById('reg-instagram').value.trim(),
        is_fresh_graduate: document.getElementById('reg-fresh').value === 'true',
        willing_outside_jakarta: document.getElementById('reg-outside').value === 'true',
        current_income: parseInt(document.getElementById('reg-income').value) || 0,
        expected_income: parseInt(document.getElementById('reg-expected').value) || 0,
        available_from: document.getElementById('reg-avail').value.trim(),
        education: [],
        training: [],
        experience: []
    };

    // Collect education
    document.querySelectorAll('.education-item').forEach(item => {
        payload.education.push({
            institution: item.querySelector('.edu-inst').value.trim(),
            major: item.querySelector('.edu-major').value.trim(),
            year: parseInt(item.querySelector('.edu-year').value) || 0,
            score: parseFloat(item.querySelector('.edu-score').value) || 0.0,
            startyear: parseInt(item.querySelector('.edu-startyear').value) || 0,
            endyear: parseInt(item.querySelector('.edu-endyear').value) || 0
        });
    });

    // Collect training
    document.querySelectorAll('.training-item').forEach(item => {
        const name = item.querySelector('.train-name').value.trim();
        if (name) {
            payload.training.push({
                name: name,
                cert_no: item.querySelector('.train-cert').value.trim(),
                startyear: parseInt(item.querySelector('.train-start').value) || 0,
                endyear: parseInt(item.querySelector('.train-end').value) || 0
            });
        }
    });

    // Collect experience
    document.querySelectorAll('.experience-item').forEach(item => {
        const company = item.querySelector('.exp-company').value.trim();
        if (company) {
            payload.experience.push({
                company: company,
                level: item.querySelector('.exp-level').value.trim(),
                jobdesk: item.querySelector('.exp-jobdesk').value.trim(),
                salary: parseFloat(item.querySelector('.exp-salary').value) || 0,
                is_current: item.querySelector('.exp-current').value === 'true',
                startyear: parseInt(item.querySelector('.exp-startyear').value) || 0,
                endyear: parseInt(item.querySelector('.exp-endyear').value) || 0
            });
        }
    });

    return payload;
}

// ═══════════════════════════════════════════════════════════════
// PORTAL HRD: TAB SWITCHER & DROPDOWN LOWONGAN
// ═══════════════════════════════════════════════════════════════

/**
 * Berpindah tab di dalam view portal HRD.
 * 
 * @param {string} tabName - Nama tab (contoh: 'overview', 'funnel').
 */
function switchHrdTab(tabName) {
    document.querySelectorAll('#hrd-view .nav-item').forEach(item => {
        item.classList.remove('active');
    });
    
    document.querySelectorAll('#hrd-view .tab-content').forEach(content => {
        content.classList.remove('active');
    });

    // Cari button nav dan aktifkan
    const btn = Array.from(document.querySelectorAll('#hrd-view .nav-item'))
        .find(item => item.getAttribute('onclick').includes(`'${tabName}'`));
    if (btn) btn.classList.add('active');

    // Aktifkan kontainer
    const content = document.getElementById(`hrd-tab-content-${tabName}`);
    if (content) content.classList.add('active');

    // Ubah title header
    updateHrdHeaderTitles(tabName);
}


/**
 * Mengubah teks judul header berdasarkan tab HRD yang aktif.
 */
function updateHrdHeaderTitles(tabName) {
    const titles = {
        overview: ["Overview Sistem", "Pantau status penyaringan CV berbasis LLM."],
        funnel: ["Pipeline Funnel", "Visualisasi eliminasi kandidat di setiap tahap filter."],
        results: ["Kandidat Lolos Seleksi", "Daftar kandidat yang lolos dengan kecocokan >= 85%."],
        eliminated: ["Transparansi Eliminasi", "Daftar kandidat yang gugur beserta alasan detailnya."],
        schema: ["ERD SQLite Portal", "Visualisasi relasi skema database portal.db."],
        settings: ["Pengaturan Kunci API", "Atur X-API-KEY perlindungan modul API."]
    };
    
    const info = titles[tabName] || ["Dashboard HRD", ""];
    document.getElementById('hrd-tab-title').textContent = info[0];
    document.getElementById('hrd-tab-desc').textContent = info[1];
}


/**
 * Mengambil daftar lowongan kerja dari SQLite untuk dropdown HRD.
 */
async function loadHrdJobsDropdown() {
    const select = document.getElementById('hrd-job-select');
    if (!select) return;
    
    select.innerHTML = '<option value="">Memuat lowongan...</option>';
    
    try {
        const res = await fetch('/api/portal/jobs');
        if (!res.ok) throw new Error("Gagal memuat lowongan kerja");
        
        const jobs = await res.json();
        if (jobs.length === 0) {
            select.innerHTML = '<option value="">Tidak ada lowongan aktif</option>';
            return;
        }
        
        select.innerHTML = jobs.map(j => 
            `<option value="${j.job_vacancy_id}">${j.job_vacancy_name}</option>`
        ).join('');
        
        activeJobId = jobs[0].job_vacancy_id;
        loadJobData();
    } catch (err) {
        select.innerHTML = '<option value="">Gagal memuat</option>';
        loggerError("Dropdown lowongan HRD", err);
    }
}

// ═══════════════════════════════════════════════════════════════
// PORTAL HRD: AMBIL DATA HASIL FILTERING & PARSING DETAIL
// ═══════════════════════════════════════════════════════════════

/**
 * Mengambil seluruh data terkait lowongan kerja yang dipilih (detail, hasil filter, eliminated).
 */
async function loadJobData() {
    const select = document.getElementById('hrd-job-select');
    if (!select || !select.value) return;
    
    activeJobId = parseInt(select.value);
    
    updateFilterStatusBox('idle', 'Sistem siap memproses filter');
    
    await Promise.all([
        loadJobDetail(),
        loadFilteringResults(),
        loadEliminatedCandidates()
    ]);
}


/**
 * Mengambil spesifikasi terstruktur lowongan kerja dari API backend FastAPI.
 */
async function loadJobDetail() {
    const apiKey = getApiKey('job');
    
    try {
        const res = await fetch(`/api/jobs/${activeJobId}`, {
            headers: { 'X-API-KEY': apiKey }
        });
        
        if (!res.ok) throw new Error("Gagal mengambil kualifikasi pekerjaan");
        
        const data = await res.json();
        renderJobTags(data.tags || []);
        
        const reqs = data.parsed_requirements;
        document.getElementById('job-parsed-requirements').textContent = 
            reqs ? JSON.stringify(reqs, null, 2) : 'Belum di-parse oleh LLM. Silakan picu parsing.';
    } catch (err) {
        document.getElementById('job-parsed-requirements').textContent = 'Error memuat data: ' + err.message;
        loggerError("Job detail", err);
    }
}


/**
 * Merender daftar tag lowongan.
 */
function renderJobTags(tags) {
    const container = document.getElementById('job-tags-list');
    if (tags.length === 0) {
        container.innerHTML = '<span class="placeholder-text">Tidak ada tag</span>';
        return;
    }
    container.innerHTML = tags.map(t => `<span class="tag">${t}</span>`).join('');
}


/**
 * Mengambil hasil seleksi kandidat yang lolos dari API backend.
 */
async function loadFilteringResults() {
    const apiKey = getApiKey('filter');
    const tableBody = document.getElementById('table-results-body');
    const countBadge = document.getElementById('badge-results-count');
    
    tableBody.innerHTML = '<tr><td colspan="7">Memuat hasil...</td></tr>';
    
    try {
        const res = await fetch(`/api/jobs/${activeJobId}/results`, {
            headers: { 'X-API-KEY': apiKey }
        });
        
        if (res.status === 202) {
            tableBody.innerHTML = '<tr><td colspan="7">Penyaringan sedang berjalan di latar belakang...</td></tr>';
            updateFilterStatusBox('running', 'Penyaringan asinkron sedang diproses di latar belakang');
            pollFilteringStatus();
            return;
        }
        
        if (!res.ok) throw new Error("Gagal memuat hasil filtering");
        
        const data = await res.json();
        renderPassedCandidates(data);
        updateStatistics(data);
        drawFunnelChart(data);
    } catch (err) {
        tableBody.innerHTML = `<tr><td colspan="7" class="text-danger">Gagal memuat hasil: ${err.message}</td></tr>`;
        loggerError("Hasil seleksi", err);
    }
}


/**
 * Merender daftar pelamar yang lolos ke dalam tabel.
 */
function renderPassedCandidates(data) {
    const tableBody = document.getElementById('table-results-body');
    const countBadge = document.getElementById('badge-results-count');
    
    const candidates = data.candidates || [];
    countBadge.textContent = `${candidates.length} Lolos`;
    
    if (candidates.length === 0) {
        tableBody.innerHTML = '<tr><td colspan="7">Tidak ada kandidat yang lolos kualifikasi.</td></tr>';
        return;
    }
    
    tableBody.innerHTML = candidates.map(c => `
        <tr>
            <td><strong>${c.name}</strong></td>
            <td><span class="text-success">${Math.round(c.total_score || c.similarity_score * 100)}%</span></td>
            <td><span class="badge ${c.is_alternative ? 'badge-warning' : 'badge-success'}">${c.is_alternative ? 'Alternatif' : 'Rekomendasi'}</span></td>
            <td>${c.tags ? c.tags.split(',').map(t => `<span class="tag" style="font-size:10px; padding:2px 6px;">${t}</span>`).join(' ') : '-'}</td>
            <td><span class="badge badge-light">${c.confidence || 'Medium'}</span></td>
            <td><span class="subtitle" style="font-size:11px;">${c.match_reason || '-'}</span></td>
            <td><button class="btn btn-outline btn-small" onclick="viewCandidateCVDetails(${c.candidate_id})">Detail CV</button></td>
        </tr>
    `).join('');
}


/**
 * Mengambil daftar kandidat yang tereliminasi beserta alasan detailnya.
 */
async function loadEliminatedCandidates() {
    const apiKey = getApiKey('filter');
    const tableBody = document.getElementById('table-eliminated-body');
    
    tableBody.innerHTML = '<tr><td colspan="3">Memuat kandidat tereliminasi...</td></tr>';
    
    try {
        const res = await fetch(`/api/jobs/${activeJobId}/eliminated`, {
            headers: { 'X-API-KEY': apiKey }
        });
        
        if (!res.ok) throw new Error("Gagal mengambil data kandidat tereliminasi");
        
        const data = await res.json();
        renderEliminatedCandidates(data);
    } catch (err) {
        tableBody.innerHTML = `<tr><td colspan="3" class="text-danger">Gagal memuat data: ${err.message}</td></tr>`;
        loggerError("Kandidat tereliminasi", err);
    }
}


/**
 * Merender daftar pelamar tereliminasi ke dalam tabel.
 */
function renderEliminatedCandidates(list) {
    const tableBody = document.getElementById('table-eliminated-body');
    
    if (list.length === 0) {
        tableBody.innerHTML = '<tr><td colspan="3">Tidak ada kandidat tereliminasi.</td></tr>';
        return;
    }
    
    tableBody.innerHTML = list.map(c => `
        <tr>
            <td><strong>${c.candidate_name}</strong></td>
            <td><span class="badge badge-danger">${c.stage}</span></td>
            <td class="text-secondary">${c.reason || 'Kriteria tidak memenuhi spesifikasi.'}</td>
        </tr>
    `).join('');
}

// ═══════════════════════════════════════════════════════════════
// STATISTICS & FUNNEL CHART (SVG)
// ═══════════════════════════════════════════════════════════════

/**
 * Memperbarui widget statistik umum di halaman overview.
 * 
 * @param {Object} data - Objek hasil filtering response.
 */
function updateStatistics(data) {
    document.getElementById('stat-total-candidates').textContent = data.total_candidates || 0;
    document.getElementById('stat-passed-candidates').textContent = data.after_taxonomy_filter || 0;
    
    const duration = data.duration_seconds || 0.0;
    document.getElementById('stat-duration').textContent = `${duration.toFixed(2)}s`;
    
    // Estimasi Hemat Waktu (5 menit per CV untuk manual check)
    const savedMinutes = (data.total_candidates || 0) * 5;
    document.getElementById('stat-saved-hours').textContent = `${savedMinutes} menit`;
}


/**
 * Menggambar diagram corong (funnel chart) SVG secara dinamis berdasarkan data kelolosan.
 * 
 * @param {Object} data - Objek hasil filtering response.
 */
function drawFunnelChart(data) {
    const container = document.getElementById('funnel-container');
    if (!container) return;
    
    const total = data.total_candidates || 0;
    const afterHard = data.after_hard_filter || 0;
    const afterSkills = data.after_skills_filter || 0;
    const finalPassed = data.after_taxonomy_filter || 0;
    
    // Hitung lebar persentase (untuk trapezoid corong)
    const w1 = 100; // top width %
    const w2 = total > 0 ? (afterHard / total) * 100 : 0;
    const w3 = afterHard > 0 ? (afterSkills / afterHard) * w2 : 0;
    const w4 = afterSkills > 0 ? (finalPassed / afterSkills) * w3 : 0;
    
    // Batasi lebar minimum agar visualisasi tetap kelihatan representatif
    const safeW2 = Math.max(w2, 15);
    const safeW3 = Math.max(w3, 10);
    const safeW4 = Math.max(w4, 5);
    
    container.innerHTML = `
        <svg viewBox="0 0 400 300" width="100%" height="100%" xmlns="http://www.w3.org/2000/svg">
            <!-- Tahap 1: Total Pelamar -->
            <polygon points="${200 - w1*1.8},10 ${200 + w1*1.8},10 ${200 + safeW2*1.8},70 ${200 - safeW2*1.8},70" fill="#e9ecef" stroke="#dee2e6" stroke-width="1"/>
            <text x="200" y="45" font-family="Inter" font-size="11" font-weight="600" text-anchor="middle" fill="#212529">1. Total Pelamar: ${total} CV</text>
            
            <!-- Tahap 2: Lolos Hard Filter -->
            <polygon points="${200 - safeW2*1.8},75 ${200 + safeW2*1.8},75 ${200 + safeW3*1.8},140 ${200 - safeW3*1.8},140" fill="#dee2e6" stroke="#ced4da" stroke-width="1"/>
            <text x="200" y="115" font-family="Inter" font-size="11" font-weight="600" text-anchor="middle" fill="#212529">2. Hard Filter: ${afterHard} CV (${Math.round(w2)}%)</text>
            
            <!-- Tahap 3: Lolos Skill Matcher -->
            <polygon points="${200 - safeW3*1.8},145 ${200 + safeW3*1.8},145 ${200 + safeW4*1.8},210 ${200 - safeW4*1.8},210" fill="#ced4da" stroke="#adb5bd" stroke-width="1"/>
            <text x="200" y="185" font-family="Inter" font-size="11" font-weight="600" text-anchor="middle" fill="#212529">3. Skill Filter: ${afterSkills} CV (${Math.round(afterHard > 0 ? (afterSkills/afterHard)*100 : 0)}%)</text>
            
            <!-- Tahap 4: Lolos Seleksi Akhir -->
            <polygon points="${200 - safeW4*1.8},215 ${200 + safeW4*1.8},215 ${200 - safeW4*1.4},280 ${200 + safeW4*1.4},280" fill="#212529" stroke="#343a40" stroke-width="1"/>
            <text x="200" y="255" font-family="Inter" font-size="11" font-weight="600" text-anchor="middle" fill="#ffffff">4. Lolos Akhir: ${finalPassed} CV (${Math.round(total > 0 ? (finalPassed/total)*100 : 0)}%)</text>
        </svg>
    `;
}

// ═══════════════════════════════════════════════════════════════
// FILTER PIPELINE EXECUTION & STATUS POLLING
// ═══════════════════════════════════════════════════════════════

/**
 * Memperbarui visual kotak status pemrosesan.
 * 
 * @param {string} state - 'idle', 'running', atau 'completed'.
 * @param {string} text - Pesan status.
 */
function updateFilterStatusBox(state, text) {
    const box = document.getElementById('filtering-status-box');
    if (!box) return;
    
    box.className = `status-box status-${state}`;
    document.getElementById('filtering-status-text').textContent = text;
}


/**
 * Memicu jalannya pipeline filtering otomatis (sinkron/asinkron).
 * 
 * @param {string} mode - 'registered' (pelamar pekerjaan) atau 'mixmatch' (seluruh DB).
 */
async function runFiltering(mode) {
    if (!activeJobId) {
        alert('Pilih lowongan kerja terlebih dahulu!');
        return;
    }
    
    const isMix = mode === 'mixmatch';
    const apiKey = getApiKey(isMix ? 'mix' : 'filter');
    const endpoint = `/api/jobs/${activeJobId}/${isMix ? 'mix-match' : 'filter'}?sync=false`;
    
    updateFilterStatusBox('running', 'Mengirimkan request pemrosesan ke Celery...');
    
    try {
        const res = await fetch(endpoint, {
            method: 'POST',
            headers: { 'X-API-KEY': apiKey }
        });
        
        if (!res.ok) {
            const errJson = await res.json();
            throw new Error(errJson.detail || "Pemicu filter gagal");
        }
        
        updateFilterStatusBox('running', 'Penyaringan sedang diproses di latar belakang (Celery & Redis)...');
        pollFilteringStatus();
    } catch (err) {
        updateFilterStatusBox('idle', 'Gagal memicu filter: ' + err.message);
        loggerError("Run filtering", err);
    }
}


/**
 * Melakukan polling status untuk memeriksa apakah penyaringan asinkron sudah selesai.
 */
function pollFilteringStatus() {
    const interval = setInterval(async () => {
        const apiKey = getApiKey('filter');
        try {
            const res = await fetch(`/api/jobs/${activeJobId}/results`, {
                headers: { 'X-API-KEY': apiKey }
            });
            
            if (res.status === 200) {
                // Selesai! Hentikan polling dan muat ulang data
                clearInterval(interval);
                updateFilterStatusBox('completed', 'Penyaringan sukses diselesaikan!');
                await Promise.all([
                    loadFilteringResults(),
                    loadEliminatedCandidates()
                ]);
            }
        } catch (err) {
            clearInterval(interval);
            updateFilterStatusBox('idle', 'Terjadi error saat memeriksa status');
            loggerError("Polling status", err);
        }
    }, 2000); // Poll setiap 2 detik
}

// ═══════════════════════════════════════════════════════════════
// ERD SCHEMA SQLITE VISUALIZER
// ═══════════════════════════════════════════════════════════════

/**
 * Mengambil skema database SQLite dan memvisualisasikan diagram ERD.
 */
async function loadErdSchema() {
    const container = document.getElementById('erd-diagram-container');
    if (!container) return;
    
    container.innerHTML = '<p>Memuat skema database...</p>';
    
    try {
        const res = await fetch('/api/portal/schema');
        if (!res.ok) throw new Error("Gagal mengambil skema SQLite");
        
        const data = await res.json();
        renderErdSchema(container, data);
    } catch (err) {
        container.innerHTML = `<p class="text-danger">Gagal memuat skema ERD: ${err.message}</p>`;
        loggerError("Load ERD", err);
    }
}


/**
 * Menggambar card ERD untuk setiap tabel beserta tipe kolom dan identifikasi PK/FK.
 * 
 * @param {HTMLElement} container - Kontainer pembungkus ERD.
 * @param {Object} schema - Objek metadata skema.
 */
function renderErdSchema(container, schema) {
    container.innerHTML = Object.keys(schema).map(tableName => {
        const columns = schema[tableName];
        
        return `
            <div class="erd-table-card">
                <div class="erd-table-name">
                    <span>${tableName}</span>
                    <span class="badge badge-light" style="font-size:9px;">SQLite</span>
                </div>
                <div class="erd-columns-list">
                    ${columns.map(col => {
                        const isPk = col.pk ? '<span class="erd-pk">🔑</span>' : '';
                        // Simulasi indikasi FK sederhana berdasarkan nama kolom
                        const isFk = (!col.pk && (col.name.endsWith('id') || col.name.endsWith('id_'))) ? '<span class="erd-fk">🔗</span>' : '';
                        
                        return `
                            <div class="erd-column-row">
                                <span class="erd-col-name">${isPk}${isFk}${col.name}</span>
                                <span class="erd-col-type">${col.type.toLowerCase()}</span>
                            </div>
                        `;
                    }).join('')}
                </div>
            </div>
        `;
    }).join('');
}

// ═══════════════════════════════════════════════════════════════
// PORTAL KANDIDAT: TAB SWITCHER & RESUME DETAIL
// ═══════════════════════════════════════════════════════════════

/**
 * Berpindah tab di dalam view portal Kandidat.
 * 
 * @param {string} tabName - 'resume' atau 'applications'.
 */
function switchCandTab(tabName) {
    document.querySelectorAll('#candidate-view .nav-item').forEach(item => {
        item.classList.remove('active');
    });
    document.querySelectorAll('#candidate-view .tab-content').forEach(content => {
        content.classList.remove('active');
    });

    // Aktifkan button nav
    const btn = Array.from(document.querySelectorAll('#candidate-view .nav-item'))
        .find(item => item.getAttribute('onclick').includes(`'${tabName}'`));
    if (btn) btn.classList.add('active');

    // Aktifkan kontainer content
    const content = document.getElementById(`cand-tab-content-${tabName}`);
    if (content) content.classList.add('active');

    // Judul header
    const info = tabName === 'resume' 
        ? ["Resume & Hasil Analisis AI", "Lihat profil Anda dan tag kualifikasi yang diekstrak oleh LLM."]
        : ["Daftar Lamaran Kerja", "Kirim lamaran baru dan pantau status kelolosan seleksi."];
        
    document.getElementById('cand-tab-title').textContent = info[0];
    document.getElementById('cand-tab-desc').textContent = info[1];
}


/**
 * Mengambil profil lengkap kandidat saat ini dari SQLite dan merendernya.
 */
async function loadCandidateProfile() {
    try {
        const res = await fetch('/api/portal/candidates');
        if (!res.ok) throw new Error("Gagal mengambil data kandidat");
        
        const list = await res.json();
        const cand = list.find(c => c.requireid === loggedCandidateId);
        if (cand) {
            renderCandidateProfileView(cand);
        }
    } catch (err) {
        alert("Gagal memuat profil kandidat.");
        loggerError("Profil kandidat", err);
    }
}


/**
 * Merender detail profil kandidat pada portal pelamar.
 * 
 * @param {Object} cand - Objek kandidat lengkap.
 */
function renderCandidateProfileView(cand) {
    document.getElementById('cand-nav-name').textContent = `${cand.firstname} ${cand.lastname || ''}`;
    document.getElementById('cand-nav-email').textContent = cand.gmail;
    
    document.getElementById('cand-profile-fullname').textContent = `${cand.firstname} ${cand.lastname || ''}`;
    document.getElementById('cand-profile-location').textContent = `${cand.city}, Indonesia`;
    document.getElementById('cand-profile-email').textContent = cand.gmail;
    document.getElementById('cand-profile-phone').textContent = cand.phone || '-';
    document.getElementById('cand-profile-gender').textContent = cand.gender || '-';
    document.getElementById('cand-profile-dob').textContent = cand.dateofbirth || '-';
    document.getElementById('cand-profile-fg').textContent = cand.is_fresh_graduate ? 'Ya' : 'Tidak';
    document.getElementById('cand-profile-salary').textContent = `Rp ${cand.q15_expected_income.toLocaleString('id-ID')}`;
    
    document.getElementById('cand-avatar-initial').textContent = cand.firstname[0].toUpperCase();
    
    renderCandidateEducationTimeline(cand.education || []);
    renderCandidateExperienceTimeline(cand.experience || []);
    loadCandidateTagsStatus();
}


/**
 * Merender daftar pendidikan ke timeline UI.
 */
function renderCandidateEducationTimeline(eduList) {
    const container = document.getElementById('cand-edu-timeline');
    if (eduList.length === 0) {
        container.innerHTML = '<p class="placeholder-text">Belum ada riwayat pendidikan.</p>';
        return;
    }
    
    container.innerHTML = eduList.map(e => `
        <div class="timeline-item">
            <div class="timeline-title">${e.institutionname}</div>
            <div class="timeline-subtitle">${e.major} (${e.startyear} - ${e.endyear})</div>
            <div class="timeline-desc">Lulus | IPK/Nilai: <strong>${e.score}</strong></div>
        </div>
    `).join('');
}


/**
 * Merender daftar pengalaman kerja ke timeline UI.
 */
function renderCandidateExperienceTimeline(expList) {
    const container = document.getElementById('cand-exp-timeline');
    if (expList.length === 0) {
        container.innerHTML = '<p class="placeholder-text">Belum ada riwayat pengalaman.</p>';
        return;
    }
    
    container.innerHTML = expList.map(e => `
        <div class="timeline-item">
            <div class="timeline-title">${e.companyname}</div>
            <div class="timeline-subtitle">${e.joblevel} (${e.startyear} - ${e.endyear})</div>
            <div class="timeline-desc">${e.jobdesk || ''}</div>
        </div>
    `).join('');
}

// ═══════════════════════════════════════════════════════════════
// PORTAL KANDIDAT: EKSTRAKSI TAG LLM & STATUS LAMARAN
// ═══════════════════════════════════════════════════════════════

/**
 * Mengambil status ekstraksi tag dan skill kandidat dari backend FastAPI.
 */
async function loadCandidateTagsStatus() {
    try {
        const res = await fetch(`/api/candidates/${loggedUserId}/tags`, {
            headers: { 'X-API-KEY': getApiKey('extract') }
        });
        
        if (!res.ok) throw new Error("Tags belum diekstrak");
        
        const data = await res.json();
        displayCandidateTags(data);
    } catch (err) {
        document.getElementById('cand-cv-tags-list').innerHTML = '<span class="placeholder-text">Belum diekstrak oleh AI. Klik tombol di atas.</span>';
        document.getElementById('cand-skills-hard').textContent = 'Belum di-parse';
        document.getElementById('cand-skills-soft').textContent = 'Belum di-parse';
    }
}


/**
 * Merender tags hasil ekstraksi LLM ke halaman portal kandidat.
 */
function displayCandidateTags(data) {
    const tagsContainer = document.getElementById('cand-cv-tags-list');
    
    if (data.tags) {
        const tagsArr = data.tags.split(',');
        tagsContainer.innerHTML = tagsArr.map(t => `<span class="tag">${t.trim()}</span>`).join('');
        document.getElementById('cand-extraction-status').className = 'status-box status-completed';
        document.getElementById('cand-extraction-text').textContent = 'CV Berhasil Diekstrak';
    }
    
    document.getElementById('cand-skills-hard').textContent = data.hard_skill || 'Tidak ada info';
    document.getElementById('cand-skills-soft').textContent = data.soft_skill || 'Tidak ada info';
}


/**
 * Memicu ekstraksi tag CV kandidat secara mandiri.
 */
async function extractTagsSelf() {
    updateCandidateExtractionBox('running', 'Menghubungi LLM untuk ekstraksi...');
    
    try {
        const res = await fetch(`/api/candidates/${loggedUserId}/extract-tags?sync=true`, {
            method: 'POST',
            headers: { 'X-API-KEY': getApiKey('extract') }
        });
        
        if (!res.ok) {
            const errJson = await res.json();
            throw new Error(errJson.detail || "Ekstraksi gagal");
        }
        
        updateCandidateExtractionBox('completed', 'Ekstraksi Sukses!');
        await loadCandidateTagsStatus();
    } catch (err) {
        updateCandidateExtractionBox('idle', 'Gagal ekstraksi: ' + err.message);
        loggerError("Ekstraksi mandiri", err);
    }
}


/**
 * Mengubah kotak status ekstraksi kandidat.
 */
function updateCandidateExtractionBox(state, text) {
    const box = document.getElementById('cand-extraction-status');
    if (!box) return;
    
    box.className = `status-box status-${state}`;
    document.getElementById('cand-extraction-text').textContent = text;
}


/**
 * Mengisi daftar lowongan pekerjaan yang bisa dilamar oleh kandidat.
 */
async function loadCandidateJobsDropdown() {
    const select = document.getElementById('cand-apply-job-select');
    if (!select) return;
    
    try {
        const res = await fetch('/api/portal/jobs');
        if (!res.ok) throw new Error("Gagal mengambil daftar lowongan");
        
        const list = await res.json();
        select.innerHTML = list.map(j => `<option value="${j.job_vacancy_id}">${j.job_vacancy_name}</option>`).join('');
    } catch (err) {
        loggerError("Dropdown lamar kandidat", err);
    }
}


/**
 * Mengirim lamaran pekerjaan baru dari kandidat.
 */
async function submitApplicationSelf() {
    const select = document.getElementById('cand-apply-job-select');
    if (!select || !select.value) return;
    
    const jobId = parseInt(select.value);
    
    try {
        const res = await fetch('/api/portal/apply', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({
                job_vacancy_id: jobId,
                user_id: loggedUserId
            })
        });
        
        if (!res.ok) throw new Error("Gagal mendaftarkan lamaran");
        
        const data = await res.json();
        alert(data.message || 'Lamaran sukses dikirim!');
        await loadCandidateApplications();
    } catch (err) {
        alert('Gagal melamar: ' + err.message);
        loggerError("Kirim lamaran", err);
    }
}


/**
 * Mengambil daftar lamaran kandidat dan status kelulusannya (dari PostgreSQL).
 */
async function loadCandidateApplications() {
    const tableBody = document.getElementById('table-cand-applications');
    if (!tableBody) return;
    
    tableBody.innerHTML = '<tr><td colspan="5">Memuat lamaran...</td></tr>';
    
    try {
        // Ambil info lowongan kerja di portal
        const jobsRes = await fetch('/api/portal/jobs');
        const jobs = await jobsRes.json();
        
        // Buat mapping ID pekerjaan ke Nama Pekerjaan
        const jobMap = {};
        jobs.forEach(j => { jobMap[j.job_vacancy_id] = j.job_vacancy_name; });
        
        // Ambil data lamaran dari PostgreSQL via check filter results masing-masing job
        const applications = [];
        
        for (const job of jobs) {
            const results = await fetchResultsForCandidate(job.job_vacancy_id);
            if (results) {
                applications.push(results);
            }
        }
        
        renderCandidateApplicationsTable(tableBody, applications);
    } catch (err) {
        tableBody.innerHTML = '<tr><td colspan="5">Gagal mengambil lamaran.</td></tr>';
        loggerError("Daftar lamaran kandidat", err);
    }
}


/**
 * Mengambil data kelolosan / eliminasi spesifik kandidat saat ini untuk lowongan tertentu.
 * 
 * @param {number} jobId - ID Lowongan Kerja.
 * @return {Object|null} Info lamaran kandidat atau null jika tidak melamar.
 */
async function fetchResultsForCandidate(jobId) {
    const apiKey = getApiKey('filter');
    
    try {
        // Cek apakah kandidat lolos seleksi
        const resPassed = await fetch(`/api/jobs/${jobId}/results`, { headers: { 'X-API-KEY': apiKey } });
        if (resPassed.ok) {
            const dataPassed = await resPassed.json();
            const candMatch = dataPassed.candidates.find(c => c.candidate_id === loggedCandidateId);
            if (candMatch) {
                return {
                    job_name: dataPassed.job_title || `Lowongan #${jobId}`,
                    date: dataPassed.last_batch_processed ? new Date(dataPassed.last_batch_processed).toLocaleDateString('id-ID') : 'Baru saja',
                    status: candMatch.is_alternative ? 'Alternatif' : 'Lolos Seleksi',
                    score: `${Math.round(candMatch.total_score || candMatch.similarity_score * 100)}%`,
                    reason: candMatch.match_reason || 'Memenuhi kriteria keahlian.'
                };
            }
        }

        // Cek apakah kandidat tereliminasi
        const resElim = await fetch(`/api/jobs/${jobId}/eliminated`, { headers: { 'X-API-KEY': apiKey } });
        if (resElim.ok) {
            const listElim = await resElim.json();
            const candMatch = listElim.find(c => c.candidate_name.includes(document.getElementById('cand-nav-name').textContent));
            if (candMatch) {
                return {
                    job_name: `Lowongan #${jobId}`,
                    date: 'Selesai diproses',
                    status: 'Tereliminasi',
                    score: '-',
                    reason: `Gugur pada tahap [${candMatch.stage}]: ${candMatch.reason || 'Kriteria tidak memenuhi.'}`
                };
            }
        }
    } catch (e) {
        loggerError(`Check job #${jobId} for candidate`, e);
    }
    return null;
}


/**
 * Merender data baris lamaran kandidat ke tabel portal.
 */
function renderCandidateApplicationsTable(tableBody, list) {
    if (list.length === 0) {
        tableBody.innerHTML = '<tr><td colspan="5">Anda belum melamar lowongan kerja apa pun.</td></tr>';
        return;
    }
    
    tableBody.innerHTML = list.map(app => {
        let statusBadge = `<span class="badge badge-light">${app.status}</span>`;
        if (app.status === 'Lolos Seleksi') {
            statusBadge = `<span class="badge badge-success">${app.status}</span>`;
        } else if (app.status === 'Alternatif') {
            statusBadge = `<span class="badge badge-warning">${app.status}</span>`;
        } else if (app.status === 'Tereliminasi') {
            statusBadge = `<span class="badge badge-danger">${app.status}</span>`;
        }
        
        return `
            <tr>
                <td><strong>${app.job_name}</strong></td>
                <td>${app.date}</td>
                <td>${statusBadge}</td>
                <td><strong class="${app.score !== '-' ? 'text-success' : ''}">${app.score}</strong></td>
                <td><span class="subtitle" style="font-size:12px;">${app.reason}</span></td>
            </tr>
        `;
    }).join('');
}

// ═══════════════════════════════════════════════════════════════
// MODAL & LOGGER UTILITIES
// ═══════════════════════════════════════════════════════════════

/**
 * Menampilkan popup modal untuk menambah lowongan baru.
 */
function showAddJobModal() {
    document.getElementById('add-job-modal').classList.add('active');
}


/**
 * Menyembunyikan popup modal tambah lowongan.
 */
function hideAddJobModal() {
    document.getElementById('add-job-modal').classList.remove('active');
    document.getElementById('new-job-title').value = '';
    document.getElementById('new-job-desc').value = '';
    document.getElementById('new-job-spec').value = '';
}


/**
 * Mengirim data lowongan baru yang diinput ke SQLite portal & PG backend.
 */
async function handleAddJobSubmit(e) {
    e.preventDefault();
    
    const payload = {
        title: document.getElementById('new-job-title').value.trim(),
        description: document.getElementById('new-job-desc').value.trim(),
        specification: document.getElementById('new-job-spec').value.trim(),
        level_name: document.getElementById('new-job-level').value.trim(),
        man_power: parseInt(document.getElementById('new-job-mp').value) || 1
    };
    
    try {
        const res = await fetch('/api/portal/jobs', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify(payload)
        });
        
        if (!res.ok) throw new Error("Gagal menyimpan lowongan kerja");
        
        alert('Lowongan pekerjaan baru berhasil ditambahkan, disinkronkan, dan proses parsing kualifikasi LLM telah dipicu di latar belakang!');
        hideAddJobModal();
        
        // Reload dropdown pekerjaan
        loadHrdJobsDropdown();
    } catch (err) {
        alert('Error menyimpan lowongan: ' + err.message);
        loggerError("Add job submit", err);
    }
}


/**
 * Menampilkan detail CV kandidat secara visual (modal/alert sederhana).
 * 
 * @param {number} candidateId - ID require dari kandidat.
 */
async function viewCandidateCVDetails(candidateId) {
    try {
        const res = await fetch('/api/portal/candidates');
        const list = await res.json();
        const cand = list.find(c => c.requireid === candidateId);
        
        if (!cand) {
            alert('Data kandidat tidak ditemukan.');
            return;
        }
        
        const eduText = cand.education.map(e => `- ${e.institutionname}, ${e.major} (Lulus ${e.year}, IPK: ${e.score})`).join('\n');
        const expText = cand.experience.map(e => `- ${e.companyname}, ${e.joblevel} (${e.startyear}-${e.endyear})\n  Jobdesk: ${e.jobdesk}`).join('\n');
        
        const details = `CV KANDIDAT: ${cand.firstname} ${cand.lastname || ''}\n` +
                        `----------------------------------------\n` +
                        `Domisili: ${cand.city}\n` +
                        `Telepon: ${cand.phone}\n` +
                        `Email: ${cand.gmail}\n` +
                        `LinkedIn: ${cand.linkedin || '-'}\n` +
                        `Instagram: ${cand.instagram || '-'}\n\n` +
                        `RIWAYAT PENDIDIKAN:\n${eduText || 'Tidak ada riwayat'}\n\n` +
                        `RIWAYAT PENGALAMAN:\n${expText || 'Tidak ada riwayat'}`;
                        
        alert(details);
    } catch (err) {
        alert('Gagal mengambil detail CV.');
        loggerError("Detail CV", err);
    }
}


/**
 * Helper logger error internal.
 * 
 * @param {string} context - Nama fungsi/modul pemanggil.
 * @param {Error} err - Kesalahan yang ditangkap.
 */
function loggerError(context, err) {
    console.error(`[ERR] Context: ${context} | Message: ${err.message}`, err);
}
