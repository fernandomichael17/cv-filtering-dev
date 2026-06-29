from app.routes.jobs import router as jobs_router
from app.routes.filtering import router as filtering_router
from app.routes.candidates import router as candidates_router

__all__ = ["jobs_router", "filtering_router", "candidates_router"]
