"""Security dependencies for API Key validation.

Defines separate validator dependencies for each API module to enforce granular access control.
"""

import secrets
from fastapi import Security, HTTPException, status
from fastapi.security.api_key import APIKeyHeader
from app.config import settings

# HTTP Header name used for API Key transmission
API_KEY_HEADER = APIKeyHeader(name="X-API-KEY", auto_error=True)


async def verify_job_parser_key(api_key: str = Security(API_KEY_HEADER)) -> str:
    """Memvalidasi API Key untuk Job Parser API secara aman terhadap timing attacks.

    Parameter:
        api_key (str): API Key dari HTTP Header X-API-KEY.

    Return:
        str: API Key yang tervalidasi.
    """
    if not secrets.compare_digest(api_key, settings.API_KEY_JOB_PARSER):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Akses Ditolak: API Key Job Parser tidak valid."
        )
    return api_key


async def verify_extract_tagger_key(api_key: str = Security(API_KEY_HEADER)) -> str:
    """Memvalidasi API Key untuk Extract Tagger API secara aman terhadap timing attacks.

    Parameter:
        api_key (str): API Key dari HTTP Header X-API-KEY.

    Return:
        str: API Key yang tervalidasi.
    """
    if not secrets.compare_digest(api_key, settings.API_KEY_EXTRACT_TAGGER):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Akses Ditolak: API Key Extract Tagger tidak valid."
        )
    return api_key


async def verify_filtering_key(api_key: str = Security(API_KEY_HEADER)) -> str:
    """Memvalidasi API Key untuk Filtering API secara aman terhadap timing attacks.

    Parameter:
        api_key (str): API Key dari HTTP Header X-API-KEY.

    Return:
        str: API Key yang tervalidasi.
    """
    if not secrets.compare_digest(api_key, settings.API_KEY_FILTERING):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Akses Ditolak: API Key Filtering tidak valid."
        )
    return api_key


async def verify_mix_match_key(api_key: str = Security(API_KEY_HEADER)) -> str:
    """Memvalidasi API Key untuk Mix-Match API secara aman terhadap timing attacks.

    Parameter:
        api_key (str): API Key dari HTTP Header X-API-KEY.

    Return:
        str: API Key yang tervalidasi.
    """
    if not secrets.compare_digest(api_key, settings.API_KEY_MIX_MATCH):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Akses Ditolak: API Key Mix-Match tidak valid."
        )
    return api_key
