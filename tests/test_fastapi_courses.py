"""
Tests for the courses catalog slice's access-control logic — the part that
matters most to get right here, since it's a straight port of
courses_routes.py's courses() route: a student locked into a primary
direction must only ever see that direction's courses (plus anything
they're already enrolled in); everyone else browses freely regardless of
the `d` query param.
"""
from fastapi.testclient import TestClient

from fastapi_app.main import app
from fastapi_app.interfaces.api.deps import get_current_user_id, get_db_session
from fastapi_app.application.courses.list_courses import list_courses_for_user
from fastapi_app.domain.courses.entities import Course, Direction

client = TestClient(app)


def _course(id, direction_id, direction_slug):
    return Course(
        id=id, slug=f"course-{id}", title=f"Course {id}", subtitle="", description="",
        level="beginner", duration_weeks=4, lessons_count=10, students_count=5, rating=4.5,
        price=0, icon="code", code_price=0, is_pro_only=0, is_paid=0,
        direction_id=direction_id, direction_name=f"Direction {direction_id}",
        direction_slug=direction_slug,
    )


class _FakeRepo:
    def __init__(self, role, primary_direction_id, all_courses, directions, enrolled_ids=None):
        self.role = role
        self.primary_direction_id = primary_direction_id
        self.all_courses = all_courses
        self.directions = directions
        self.enrolled_ids = enrolled_ids or set()
        self.captured_filter = None

    def get_user_access(self, user_id):
        return self.role, self.primary_direction_id

    def get_direction_by_id(self, direction_id):
        return next((d for d in self.directions if d.id == direction_id), None)

    def list_active_directions(self):
        return self.directions

    def get_enrolled_course_ids(self, user_id):
        return self.enrolled_ids

    def list_courses(self, direction_slug, also_include_course_ids, search, level, limit):
        self.captured_filter = (direction_slug, also_include_course_ids)
        courses = self.all_courses
        if direction_slug and also_include_course_ids:
            courses = [c for c in courses if c.direction_slug == direction_slug or c.id in also_include_course_ids]
        elif direction_slug:
            courses = [c for c in courses if c.direction_slug == direction_slug]
        return courses


def teardown_function():
    app.dependency_overrides.clear()


def test_non_student_is_not_locked_but_d_param_still_filters_normally():
    """Non-students aren't access-controlled by direction, but `d` is a
    normal category filter for them too (not a security bypass check)."""
    repo = _FakeRepo(
        role="admin", primary_direction_id=None,
        all_courses=[_course(1, 1, "web"), _course(2, 2, "mobile")],
        directions=[Direction(id=1, slug="web", name_uz="Web", icon="", description="", color="")],
    )
    filtered, _ = list_courses_for_user(repo, user_id=1, direction_slug="web", search=None, level=None)
    assert len(filtered) == 1 and filtered[0].direction_slug == "web"

    unfiltered, _ = list_courses_for_user(repo, user_id=1, direction_slug=None, search=None, level=None)
    assert len(unfiltered) == 2  # no `d` at all: admin sees everything


def test_student_with_no_direction_browses_freely():
    repo = _FakeRepo(
        role="student", primary_direction_id=None,
        all_courses=[_course(1, 1, "web"), _course(2, 2, "mobile")],
        directions=[],
    )
    courses, _ = list_courses_for_user(repo, user_id=1, direction_slug=None, search=None, level=None)
    assert len(courses) == 2


def test_student_locked_to_primary_direction():
    direction = Direction(id=1, slug="web", name_uz="Web", icon="", description="", color="")
    repo = _FakeRepo(
        role="student", primary_direction_id=1,
        all_courses=[_course(1, 1, "web"), _course(2, 2, "mobile")],
        directions=[direction],
    )
    courses, directions = list_courses_for_user(repo, user_id=1, direction_slug="mobile", search=None, level=None)
    # locked direction OVERRIDES the d=mobile query param
    assert len(courses) == 1
    assert courses[0].direction_slug == "web"
    assert directions == [direction]


def test_student_locked_direction_still_sees_enrolled_course_outside_it():
    direction = Direction(id=1, slug="web", name_uz="Web", icon="", description="", color="")
    repo = _FakeRepo(
        role="student", primary_direction_id=1,
        all_courses=[_course(1, 1, "web"), _course(2, 2, "mobile")],
        directions=[direction],
        enrolled_ids={2},  # enrolled in a course OUTSIDE their locked direction
    )
    courses, _ = list_courses_for_user(repo, user_id=1, direction_slug=None, search=None, level=None)
    ids = {c.id for c in courses}
    assert ids == {1, 2}  # both the locked-direction course AND the exception


def test_router_requires_auth():
    resp = client.get("/api/v2/courses")
    assert resp.status_code == 401
