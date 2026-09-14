"""
Phase 1 coexistence entrypoint.

FastAPI is the top-level ASGI app. New, ported domains get real FastAPI
routers (e.g. sandbox below). Everything else falls through to the existing
Flask app, mounted as a WSGI sub-application — so during the migration,
every route that hasn't been ported yet keeps working completely unchanged.

Run locally with:
    uvicorn fastapi_app.main:app --reload

Production (Procfile):
    gunicorn --workers 1 --worker-class uvicorn.workers.UvicornWorker --timeout 60 fastapi_app.main:app

--workers must stay 1 for the same reason it did under run_all.py: more than
one worker would each start its own Telegram bot poller and collide (409).
"""
from fastapi import FastAPI
from a2wsgi import WSGIMiddleware

import run_all  # bootstraps the Telegram bot thread as an import side effect,
                 # then exposes run_all.app (the Flask app) — same as the old
                 # `gunicorn ... run_all:app` did, just imported here instead.
from fastapi_app.interfaces.api.routers import (
    sandbox, me, coins, ids, certificates, notifications, friends, messages, enrollments, badges, forum,
    startups, courses, groups, library, leaderboard, mentors, freelance, career, incubator, securityzone,
    shatslive, organization, teacher, pentest, bejik,
)

api = FastAPI(title="CYBER SHATS (Phase 1)")
api.include_router(sandbox.router)
api.include_router(me.router)
api.include_router(coins.router)
api.include_router(ids.router)
api.include_router(certificates.router)
api.include_router(notifications.router)
api.include_router(friends.router)
api.include_router(messages.router)
api.include_router(enrollments.router)
api.include_router(badges.router)
api.include_router(forum.router)
api.include_router(startups.router)
api.include_router(courses.router)
api.include_router(groups.router)
api.include_router(library.router)
api.include_router(leaderboard.router)
api.include_router(mentors.router)
api.include_router(freelance.router)
api.include_router(career.router)
api.include_router(incubator.router)
api.include_router(securityzone.router)
api.include_router(shatslive.router)
api.include_router(organization.router)
api.include_router(teacher.router)
api.include_router(pentest.router)
api.include_router(bejik.router)

# Anything not matched by a FastAPI route above falls through to the
# existing Flask app, unchanged.
api.mount("/", WSGIMiddleware(run_all.app))

app = api
