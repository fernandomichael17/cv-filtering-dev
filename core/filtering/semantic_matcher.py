"""Layer 2 Fallback — Semantic Embedding Matcher for Unknown Titles (Opsi B).

Uses a lightweight multilingual sentence transformer to find the closest matching
ISCO code for job titles that fail the keyword dictionary lookup.
"""

import hashlib
import json
import logging
import os
import torch
import numpy as np
from sentence_transformers import SentenceTransformer
from sklearn.metrics.pairwise import cosine_similarity

from app.config import settings
from core.utils.taxonomy import TITLE_TO_ISCO
from core.utils.db_cache import SQLiteCache
from core.utils.text_normalizer import normalize_text
from core.observability.metrics import get_metrics

logger = logging.getLogger(__name__)

# Config
MODEL_NAME = settings.SIMILARITY_MODEL
SIMILARITY_THRESHOLD = settings.SIMILARITY_THRESHOLD_ISCO_FALLBACK

class SemanticTaxonomyMatcher:
    def __init__(self):
        self.model = None
        self.titles = []
        self.codes = []
        self.embeddings = None
        self.is_initialized = False
        self._db_cache = None

    def initialize(self):
        """Melakukan inisialisasi tertunda (lazy initialization) untuk memuat model dan menghitung awal embeddings.

        Deskripsi:
            Fungsi ini memuat model SentenceTransformer ke memori, membatasi penggunaan
            thread CPU menjadi maksimal 2 thread untuk mencegah interferensi sumber daya dengan chatbot,
            dan memuat cache embedding taksonomi jika tersedia di disk.

        Parameter:
            Tidak ada.

        Return:
            Tidak ada (None).
        """
        if self.is_initialized:
            return

        # Batasi penggunaan thread PyTorch di CPU agar chatbot tidak kekurangan resource
        import torch
        torch.set_num_threads(2)

        device = settings.SIMILARITY_DEVICE
        if device == "auto":
            import torch
            device = "cuda" if torch.cuda.is_available() else "cpu"

        logger.info(f"Loading Semantic Fallback Model '{MODEL_NAME}' on device '{device}'...")
        try:
            self.model = SentenceTransformer(MODEL_NAME, device=device)
            
            # Prepare our knowledge base from job_taxonomy.json only (broader categories)
            # to keep semantic search fast and avoid precomputing 30,000+ embeddings.
            from core.utils.taxonomy import BASE_ISCO, KBJI_ALIASES
            
            base_mappings = {}
            for code, name in BASE_ISCO.items():
                if name:
                    base_mappings[name.lower().strip()] = code
            for code, aliases in KBJI_ALIASES.items():
                for alias in aliases:
                    if alias:
                        base_mappings[alias.lower().strip()] = code
                        
            self.titles = list(base_mappings.keys())
            self.codes = list(base_mappings.values())
            
            # --- Automatic Disk Caching Mechanism ---
            cache_dir = os.path.normpath(os.path.join(os.path.dirname(__file__), '..', '..', '..', 'data'))
            os.makedirs(cache_dir, exist_ok=True)
            cache_path = os.path.join(cache_dir, 'semantic_cache.npz')
            db_path = os.path.join(cache_dir, 'filtering_cache.db')
            
            # Inisialisasi SQLite persistent cache
            self._db_cache = SQLiteCache(db_path)
            
            # Create a hash of the current model, titles, and codes to invalidate cache if taxonomy or model changes
            hash_content = json.dumps({"model": MODEL_NAME, "titles": self.titles, "codes": self.codes}, sort_keys=True)
            data_hash = hashlib.md5(hash_content.encode('utf-8')).hexdigest()
            
            cache_loaded = False
            if os.path.exists(cache_path):
                try:
                    with np.load(cache_path) as data:
                        if 'hash' in data and data['hash'].item() == data_hash:
                            logger.info("Loading pre-computed embeddings from disk cache...")
                            self.embeddings = data['embeddings']
                            cache_loaded = True
                        else:
                            logger.info("Semantic cache invalid or hash mismatch. Rebuilding...")
                except Exception as e:
                    logger.warning(f"Failed to load semantic cache: {e}. Rebuilding...")

            if not cache_loaded:
                logger.info(f"Computing embeddings for {len(self.titles)} known taxonomy titles (this may take a while)...")
                prefixed_titles = [f"passage: {t}" for t in self.titles]
                self.embeddings = self.model.encode(prefixed_titles, convert_to_numpy=True, show_progress_bar=False)
                
                try:
                    np.savez(cache_path, embeddings=self.embeddings, hash=data_hash)
                    logger.info("Embeddings successfully cached to disk.")
                except Exception as e:
                    logger.warning(f"Failed to save semantic cache to disk: {e}")
            # ----------------------------------------
            
            self.is_initialized = True
            logger.info("Semantic Fallback Model ready.")
        except Exception as e:
            logger.error(f"Failed to initialize SemanticTaxonomyMatcher: {e}")

    def get_embedding(self, text: str) -> np.ndarray:
        """Get or compute sentence embedding for a string, using SQLite cache."""
        if not self.is_initialized:
            self.initialize()
            
        text_clean = text.strip().lower()
        if not text_clean:
            return np.zeros((768,))  # Fallback zero vector

        # Gunakan SQLite cache
        cache_key = f"emb:{MODEL_NAME}:{text_clean}"
        cached_val = self._db_cache.get(cache_key)
        
        metrics = get_metrics()
        
        if cached_val is not None:
            if metrics:
                metrics.record_cache_hit()
            return cached_val
            
        # Encode single text
        if metrics:
            metrics.record_cache_miss()
            
        emb = self.model.encode([text_clean], convert_to_numpy=True, show_progress_bar=False)[0]
        self._db_cache.set(cache_key, emb)
        return emb

    def find_best_isco_code(self, query_title: str) -> str:
        """Find the most semantically similar ISCO code for an unknown title."""
        if not self.is_initialized:
            self.initialize()
            
        if not self.is_initialized or not query_title:
            return "unknown"
            
        # Clean the query
        query = query_title.strip().lower()
        if not query:
            return "unknown"
            
        # Normalisasi untuk memperbaiki Typo (contoh: digtal -> digital) dan memetakan sinonim
        query = normalize_text(query, self.titles)

        # Use cached embedding with "query: " prefix for E5
        prefixed_query = f"query: {query}"
        query_emb = self.get_embedding(prefixed_query).reshape(1, -1)
        
        # Calculate cosine similarity against all pre-computed titles
        similarities = cosine_similarity(query_emb, self.embeddings)[0]
        
        # Find the best match
        best_idx = np.argmax(similarities)
        best_score = similarities[best_idx]
        best_title = self.titles[best_idx]
        best_code = self.codes[best_idx]
        
        if best_score >= SIMILARITY_THRESHOLD:
            logger.debug(
                f"[Semantic Fallback] '{query}' -> matched '{best_title}' "
                f"(ISCO {best_code}) with score {best_score:.2f} >= {SIMILARITY_THRESHOLD}"
            )
            return best_code
        else:
            logger.debug(
                f"[Semantic Fallback] '{query}' -> closest was '{best_title}' "
                f"with score {best_score:.2f} < {SIMILARITY_THRESHOLD}. Returning unknown."
            )
            return "unknown"

    def calculate_max_similarity(self, query: str, targets: list[str]) -> tuple[float, str]:
        """Calculate max cosine similarity between a query and a list of target strings.
        
        Returns:
            (max_score, best_match_string)
        """
        if not query or not targets:
            return 0.0, ""
            
        if not self.is_initialized:
            self.initialize()
            if not self.is_initialized:
                return 0.0, ""
                
        # Clean inputs
        query_clean = query.strip().lower()
        targets_clean = [t.strip().lower() for t in targets if t.strip()]
        
        if not query_clean or not targets_clean:
            return 0.0, ""
            
        # Normalisasi teks query (misal: "digtal" di-replace jadi target yang cocok di target array)
        query_clean = normalize_text(query_clean, targets_clean)
            
        # Get cached embeddings with E5 prefixes
        prefixed_query = f"query: {query_clean}"
        query_emb = self.get_embedding(prefixed_query).reshape(1, -1)
        targets_embs = np.array([self.get_embedding(f"passage: {t}") for t in targets_clean])
        
        # Calculate
        similarities = cosine_similarity(query_emb, targets_embs)[0]
        
        best_idx = np.argmax(similarities)
        return float(similarities[best_idx]), targets_clean[best_idx]

    def prewarm_cache(self, texts: list[str]):
        """Batch encode a list of texts and populate the SQLite cache."""
        if not self.is_initialized:
            self.initialize()
            if not self.is_initialized or not self.model:
                return
                
        # Filter out texts that are already cached
        uncached_texts = []
        cache_keys = []
        for t in texts:
            if not t:
                continue
            t_clean = t.strip().lower()
            if t_clean:
                cache_key = f"emb:{MODEL_NAME}:{t_clean}"
                if self._db_cache.get(cache_key) is None:
                    uncached_texts.append(t_clean)
                    cache_keys.append(cache_key)
                
        if not uncached_texts:
            return
            
        logger.info(f"Pre-warming SQLite cache with {len(uncached_texts)} new texts...")
        try:
            # Batch encode
            embs = self.model.encode(
                uncached_texts,
                batch_size=64,
                convert_to_numpy=True,
                show_progress_bar=False
            )
            for cache_key, emb in zip(cache_keys, embs):
                self._db_cache.set(cache_key, emb)
            logger.info("SQLite cache pre-warmed successfully.")
        except Exception as e:
            logger.error(f"Failed to pre-warm SQLite cache: {e}")

# Singleton instance
semantic_matcher = SemanticTaxonomyMatcher()
