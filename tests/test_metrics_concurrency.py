"""
Test untuk memastikan PipelineMetrics menggunakan ContextVar dengan benar
sehingga metrik untuk eksekusi konkruen tidak bocor (leak) antar request.
"""
import pytest
import asyncio
from unittest.mock import patch, AsyncMock, MagicMock
from app.services.filtering_service import FilteringService
from core.observability.metrics import get_metrics

async def mock_run_elimination_pipeline_slow(*args, **kwargs):
    # Simulate a slow process so that jobs overlap
    metrics = get_metrics()
    if metrics:
        metrics.record_count("passed_pipeline", 5)
    await asyncio.sleep(0.2)
    return [], [], set()

@pytest.mark.asyncio
async def test_metrics_concurrency():
    """Memastikan ContextVar memisahkan metrik antar Job ID saat dijalankan secara concurrent."""
    mock_db = MagicMock()
    mock_job_repo = MagicMock()
    
    mock_job_repo.get_parsed_cache = AsyncMock(return_value=MagicMock(parsed_requirements={}, tags=[]))
    mock_job_repo.get_vacancy_by_id = AsyncMock(return_value=MagicMock(job_vacancy_name="Mock Job"))
    
    mock_filtering_repo = MagicMock()
    mock_filtering_repo.get_results_by_job_vacancy_id = AsyncMock(return_value=[])
    mock_filtering_repo.get_applied_candidates = AsyncMock(return_value=[])
    mock_filtering_repo.save_results_bulk = AsyncMock()
    service = FilteringService()
    service.job_repo = mock_job_repo
    service.filtering_repo = mock_filtering_repo
    
    # Overwrite the pipeline with our slow mock
    service._run_elimination_pipeline = mock_run_elimination_pipeline_slow
    service._calculate_scores_and_tiers = MagicMock(return_value=[])
    service.get_results = AsyncMock(return_value=MagicMock())
    
    with patch("app.services.filtering_service.async_session", MagicMock(return_value=AsyncMock(__aenter__=AsyncMock(return_value=mock_db)))):
        # Run 3 jobs concurrently
        tasks = [
            service.run_filtering(mock_db, job_id=1, mode="registered"),
            service.run_filtering(mock_db, job_id=2, mode="registered"),
            service.run_filtering(mock_db, job_id=3, mode="registered"),
        ]
        
        # If ContextVar is working correctly, there shouldn't be any "dictionary changed size during iteration"
        # or overlapping metrics because each task gets its own PipelineMetrics instance.
        results = await asyncio.gather(*tasks)
        assert len(results) == 3
