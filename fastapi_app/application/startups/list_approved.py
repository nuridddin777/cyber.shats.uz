from fastapi_app.domain.startups.entities import Startup
from fastapi_app.domain.startups.repository import StartupsRepository


def list_approved(repo: StartupsRepository, viewer_user_id: int, limit: int = 100) -> list[Startup]:
    return repo.list_approved(viewer_user_id, limit)
