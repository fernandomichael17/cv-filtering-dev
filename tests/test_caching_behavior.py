"""
Test untuk memastikan bahwa modul semantic_matcher benar-benar memanfaatkan
SQLiteCache dan mencatat hit rate pada PipelineMetrics.
"""
import pytest
from unittest.mock import patch, MagicMock
from core.filtering.semantic_matcher import semantic_matcher, SemanticTaxonomyMatcher
from core.observability.metrics import PipelineMetrics, current_metrics
import numpy as np

@pytest.fixture(autouse=True)
def reset_matcher():
    """Ensure we start with a clean semantic_matcher state if needed."""
    yield
    
@pytest.mark.asyncio
async def test_semantic_matcher_cache_hits_and_misses():
    """Memastikan caching berfungsi dengan memanggil get_embedding dua kali."""
    
    # Buat metrics instance dan set ke ContextVar
    metrics = PipelineMetrics(job_id=999)
    token = current_metrics.set(metrics)
    
    try:
        # Create a fresh matcher with a mocked model and cache to isolate the test
        test_matcher = SemanticTaxonomyMatcher()
        test_matcher.is_initialized = True
        
        # Mock SQLiteCache
        mock_cache = dict()
        mock_sqlite = MagicMock()
        mock_sqlite.get.side_effect = lambda k: mock_cache.get(k)
        mock_sqlite.set.side_effect = lambda k, v: mock_cache.update({k: v})
        test_matcher._db_cache = mock_sqlite
        
        # Mock Model
        mock_model = MagicMock()
        # Return a dummy vector
        mock_model.encode.return_value = [np.array([0.1, 0.2, 0.3])]
        test_matcher.model = mock_model
        
        # 1. Panggilan Pertama (Harus Cache Miss)
        emb1 = test_matcher.get_embedding("Software Engineer")
        assert metrics.semantic_cache["misses"] == 1
        assert metrics.semantic_cache["hits"] == 0
        assert mock_model.encode.call_count == 1
        
        # 2. Panggilan Kedua (Harus Cache Hit)
        emb2 = test_matcher.get_embedding("Software Engineer")
        assert metrics.semantic_cache["misses"] == 1
        assert metrics.semantic_cache["hits"] == 1
        assert mock_model.encode.call_count == 1 # Tidak boleh bertambah
        
        # Pastikan embedingnya identik
        assert np.array_equal(emb1, emb2)
        
    finally:
        current_metrics.reset(token)
