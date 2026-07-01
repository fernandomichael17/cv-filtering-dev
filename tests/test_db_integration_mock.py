"""
Test untuk memastikan sistem menangani kegagalan Database API (ProgrammingError) secara elegan.
"""
import pytest
from unittest.mock import patch, MagicMock, AsyncMock
from app.services.filtering_service import FilteringService
import sqlalchemy.exc

@pytest.mark.asyncio
async def test_filtering_service_handles_db_programming_error():
    """Memastikan bahwa error pada query SQL (seperti ProgrammingError karena tabel tidak ada) tidak men-crash aplikasi tanpa logging."""
    mock_db = MagicMock()
    mock_job_repo = MagicMock()
    mock_filtering_repo = MagicMock()
    
    # Simulate DB Error when trying to get_parsed_cache
    mock_job_repo.get_parsed_cache.side_effect = sqlalchemy.exc.ProgrammingError(
        statement="SELECT * FROM parsed_job_cache", params={}, orig=Exception("Table not found")
    )
    service = FilteringService()
    service.job_repo = mock_job_repo
    service.filtering_repo = mock_filtering_repo
    
    # We expect the error to propagate up so the task can log it and fail gracefully
    # The run_filtering_task catches it and logs it, preventing app crash
    
    with patch("app.services.filtering_service.async_session", MagicMock(return_value=AsyncMock(__aenter__=AsyncMock(return_value=mock_db)))):
        # Because run_filtering_task catches the exception, it shouldn't raise outwards
        await service.run_filtering_task(job_id=99, mode="registered")
        
        # Verify get_parsed_cache was actually called
        mock_job_repo.get_parsed_cache.assert_called_with(mock_db, 99)
