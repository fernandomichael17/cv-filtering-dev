"""
Modul Observabilitas dan Metrik untuk Alur Penyaringan (Filtering Pipeline).
Modul ini bertugas mencatat latensi, drop-off kandidat per-stage, serta efisiensi cache semantik.
"""

import time
import logging
import json
from contextlib import contextmanager
from contextvars import ContextVar

logger = logging.getLogger(__name__)

class PipelineMetrics:
    """Kelas in-memory untuk mengumpulkan metrik pipeline penyaringan per Job ID."""
    
    def __init__(self, job_id: int):
        self.job_id = job_id
        self.latencies = {}
        self.candidate_counts = {}
        self.semantic_cache = {"hits": 0, "misses": 0}
        self.start_time = time.time()
        
    def record_count(self, stage: str, count: int):
        """Mencatat jumlah kandidat yang bertahan di sebuah stage (funnel)."""
        self.candidate_counts[stage] = count
        
    def record_cache_hit(self):
        """Mencatat ketika embedding ditemukan di Redis (cache hit)."""
        self.semantic_cache["hits"] += 1
        
    def record_cache_miss(self):
        """Mencatat ketika embedding tidak ditemukan dan harus dimuat dari LLM (cache miss)."""
        self.semantic_cache["misses"] += 1
        
    def add_latency(self, stage: str, duration: float):
        """Menambahkan durasi waktu ke stage tertentu."""
        if stage not in self.latencies:
            self.latencies[stage] = 0.0
        self.latencies[stage] += duration
        
    @contextmanager
    def measure_latency(self, stage: str):
        """Context manager untuk mengukur durasi suatu blok kode."""
        start = time.time()
        try:
            yield
        finally:
            duration = time.time() - start
            self.add_latency(stage, duration)

    def log_report(self):
        """Menghasilkan laporan observasi dalam bentuk JSON di log."""
        total_duration = time.time() - self.start_time
        
        cache_total = self.semantic_cache["hits"] + self.semantic_cache["misses"]
        hit_rate = 0.0
        if cache_total > 0:
            hit_rate = (self.semantic_cache["hits"] / cache_total) * 100.0

        report = {
            "job_id": self.job_id,
            "total_duration_sec": round(total_duration, 3),
            "latencies_sec": {k: round(v, 3) for k, v in self.latencies.items()},
            "funnel_counts": self.candidate_counts,
            "semantic_cache": {
                "hits": self.semantic_cache["hits"],
                "misses": self.semantic_cache["misses"],
                "hit_rate_pct": round(hit_rate, 1)
            }
        }
        
        logger.info(f"OBSERVABILITY METRICS [Job {self.job_id}]: {json.dumps(report)}")

# Variabel context global (aman untuk concurrency dengan asyncio)
current_metrics = ContextVar("current_metrics", default=None)

def get_metrics() -> PipelineMetrics | None:
    return current_metrics.get()

