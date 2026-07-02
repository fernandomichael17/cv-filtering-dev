"""Application configuration using pydantic-settings."""

from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    """Application settings loaded from environment variables."""

    # LLM Configuration (used for JD parsing & tag extraction)
    LLM_API_BASE: str = "http://localhost:8000/v1"
    LLM_MODEL_NAME: str = "Qwen/Qwen3.5-4B"
    LLM_API_KEY: str = ""
    MAX_CONCURRENT_LLM: int = 5
    LLM_TIMEOUT: int = 30  # Batas waktu panggilan LLM dalam detik
    LLM_MAX_RETRIES: int = 3  # Jumlah maksimal percobaan ulang panggilan LLM jika gagal
    ENABLE_LLM_EVALUATOR: bool = False  # Toggle LLM confidence evaluator (on/off)
    ENABLE_INDUSTRY_BONUS: bool = False  # Toggle bonus skor industri property (on/off)
    USE_STANDARDIZED_TITLE_FOR_TAXO: bool = True  # Toggle penggunaan nama jabatan standar hasil LLM untuk klasifikasi taksonomi (on/off)

    # Similarity Model Configuration
    # SIMILARITY_MODEL: str = "jinaai/jina-colbert-v2"
    # SIMILARITY_THRESHOLD: float = 5.0
    SIMILARITY_MODEL: str = "intfloat/multilingual-e5-base"
    SIMILARITY_THRESHOLD: float = 0.86
    SIMILARITY_THRESHOLD_REQUIRED: float = 0.85
    SIMILARITY_THRESHOLD_PREFERRED: float = 0.86
    SIMILARITY_DEVICE: str = "auto"  # "auto", "cuda", or "cpu"

    # Threshold Semantik Terkonsolidasi (P4)
    SIMILARITY_THRESHOLD_MAJOR: float = 0.86                  # Batas kemiripan jurusan di hard filter
    SIMILARITY_THRESHOLD_CERTIFICATION: float = 0.85          # Batas kemiripan sertifikasi di hard filter
    SIMILARITY_THRESHOLD_TAXONOMY_SKILLS: float = 0.92        # Batas kemiripan keahlian taksonomi
    SIMILARITY_THRESHOLD_TAXONOMY_EXP_SKILLS: float = 0.85    # Batas kemiripan keahlian dalam jobdesk
    SIMILARITY_THRESHOLD_SCORING_CERT: float = 0.80           # Batas kemiripan sertifikasi di scoring
    SIMILARITY_THRESHOLD_SCORING_SKILL: float = 0.80          # Batas kemiripan keahlian di scoring
    SIMILARITY_THRESHOLD_ISCO_FALLBACK: float = 0.82          # Batas kemiripan fallback taksonomi ISCO
    SIMILARITY_THRESHOLD_SCORING_CERT_BONUS: float = 0.65     # Batas kemiripan untuk bonus sertifikat relevan
    SIMILARITY_THRESHOLD_JOBDESK: float = 0.72                # Batas kemiripan untuk evaluasi free-text jobdesk
    SIMILARITY_THRESHOLD_FALLBACK: float = 0.60               # Batas longgar kemiripan fallback taksonomi/pengalaman

    # Bobot Adaptif Fresh Graduate (digunakan di scoring.py)
    FG_WEIGHT_TAXONOMY: float = 0.60       # Taksonomi kurang relevan untuk FG
    FG_WEIGHT_EXPERIENCE: float = 0.10     # Pengalaman minimal untuk FG
    FG_WEIGHT_EDUCATION: float = 1.80      # Pendidikan ditingkatkan
    FG_WEIGHT_MAJOR: float = 1.50          # Jurusan ditingkatkan
    FG_WEIGHT_GPA: float = 2.40            # IPK sangat penting
    FG_WEIGHT_CERTIFICATION: float = 1.20  # Sertifikasi ditingkatkan
    FG_WEIGHT_SKILLS: float = 1.80         # Keahlian ditingkatkan
    FG_WEIGHT_JOBDESK: float = 0.00        # Jobdesk tidak dihitung untuk FG

    # Database Configuration
    DB_USER: str = ""
    DB_PASSWORD: str = ""
    DB_HOST: str = ""
    DB_PORT: int = 5432
    DB_NAME: str = ""

    # Redis Configuration
    REDIS_HOST: str = "localhost"
    REDIS_PORT: int = 6379
    REDIS_DB: int = 0
    REDIS_PASSWORD: str | None = None

    @property
    def CELERY_BROKER_URL(self) -> str:
        pwd = f":{self.REDIS_PASSWORD}@" if self.REDIS_PASSWORD else ""
        return f"redis://{pwd}{self.REDIS_HOST}:{self.REDIS_PORT}/{self.REDIS_DB}"

    @property
    def CELERY_RESULT_BACKEND(self) -> str:
        return self.CELERY_BROKER_URL


    # Application Settings
    APP_TITLE: str = "CV Filtering API"
    DEBUG: bool = False

    # Granular API Key Protection (Loaded from .env)
    API_KEY_JOB_PARSER: str = ""
    API_KEY_EXTRACT_TAGGER: str = ""
    API_KEY_FILTERING: str = ""
    API_KEY_MIX_MATCH: str = ""

    @property
    def DATABASE_URL(self) -> str:
        # Menghapus karakter spasi dan carriage return (\r) dari konfigurasi database
        import urllib.parse
        db_user = self.DB_USER.strip()
        db_pass = urllib.parse.quote_plus(self.DB_PASSWORD.strip())
        db_host = self.DB_HOST.strip()
        db_name = self.DB_NAME.strip()
        return (
            f"postgresql+asyncpg://{db_user}:{db_pass}"
            f"@{db_host}:{self.DB_PORT}/{db_name}"
        )


    model_config = {
        "env_file": ".env", 
        "env_file_encoding": "utf-8",
        "extra": "ignore"
    }


settings = Settings()
# Trigger reload to load new env thresholds

