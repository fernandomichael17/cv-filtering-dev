"""
Test untuk memastikan sistem menangani kegagalan LLM API (Timeout, Connection Refused, Bad JSON) secara elegan.
"""
import pytest
from unittest.mock import patch, MagicMock, AsyncMock
from core.llm.jd_parser import parse_job_description
from app.services.filtering_service import FilteringService
import httpx
import json

@pytest.mark.asyncio
async def test_jd_parser_timeout_exception():
    """Memastikan bahwa parse_job_description melempar ValueError yang tertangani saat LLM Timeout."""
    # Patch call_llm (yang memanggil API) agar melempar exception HTTP
    with patch("core.llm.jd_parser.call_llm", side_effect=httpx.TimeoutException("Connection timeout to LLM")):
        with pytest.raises(ValueError, match="Gagal parsing JD"):
            await parse_job_description("Dibutuhkan programmer handal")

@pytest.mark.asyncio
async def test_jd_parser_bad_json_fallback():
    """Memastikan bahwa jika LLM mengembalikan JSON yang benar-benar rusak setelah retries, ia akan melempar ValueError."""
    bad_json_response = '{"required_skills": ["Python", '
    
    with patch("core.llm.jd_parser.call_llm", return_value=bad_json_response):
        with pytest.raises(ValueError, match="Gagal parsing JD"):
            await parse_job_description("Dibutuhkan programmer handal")

@pytest.mark.asyncio
async def test_filtering_service_handles_jd_parser_failure():
    """Memastikan FilteringService tidak crash saat parsing gagal, dan fallback ke cache kosong."""
    mock_db = MagicMock()
    mock_job_repo = MagicMock()
    
    mock_job_repo.upsert_parsed_cache = AsyncMock()
    
    service = FilteringService()
    service.job_repo = mock_job_repo
    service.filtering_repo = MagicMock()
    
    with patch("app.services.filtering_service.parse_job_description", side_effect=ValueError("LLM Down")):
        with patch.object(service, "run_filtering", new_callable=AsyncMock):
            with patch("app.services.filtering_service.async_session", MagicMock(return_value=AsyncMock(__aenter__=AsyncMock(return_value=mock_db)))):
                # Ini tidak boleh throw exception
                await service.parse_and_filter_task(job_id=99, title="Backend", description="Python Developer")
                
                # Verifikasi fallback upsert_parsed_cache dipanggil dengan dict kosong
                mock_job_repo.upsert_parsed_cache.assert_called_with(mock_db, 99, {}, [])
