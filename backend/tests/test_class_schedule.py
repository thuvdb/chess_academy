"""
Unit tests for Sprint 2 (CAMS-0004): class schedule normalization and endpoint wiring.
Run: $env:PYTHONIOENCODING='utf-8'; python tests/test_class_schedule.py
"""

import sys
import os
import uuid

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from app.services.class_service import normalize_schedule_slots


def test_normalize_standard_shape():
    print("=" * 60)
    print("TEST: Schedule normalization - standard shape")
    print("=" * 60)

    # Days deliberately out of week order to prove sorting
    slots = normalize_schedule_slots({"Wed": ["17:00"], "Mon": ["19:00", "07:30"]})
    assert slots == [
        {"day": "Mon", "time": "07:30"},
        {"day": "Mon", "time": "19:00"},
        {"day": "Wed", "time": "17:00"},
    ], f"Unexpected slots: {slots}"
    print("  [PASS] Slots sorted Mon-first, then by time")

    full_week = normalize_schedule_slots({
        "Sun": ["08:00"], "Sat": ["08:00"], "Fri": ["08:00"],
        "Thu": ["08:00"], "Wed": ["08:00"], "Tue": ["08:00"], "Mon": ["08:00"],
    })
    assert [s["day"] for s in full_week] == ["Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"], \
        f"Week order wrong: {[s['day'] for s in full_week]}"
    print("  [PASS] Full week sorted Mon -> Sun")


def test_normalize_tolerates_loose_input():
    print("\n" + "=" * 60)
    print("TEST: Schedule normalization - loose input")
    print("=" * 60)

    # schedule_json is a free-form JSONB column, so bad shapes must not raise
    assert normalize_schedule_slots(None) == [], "None should yield no slots"
    assert normalize_schedule_slots({}) == [], "Empty dict should yield no slots"
    assert normalize_schedule_slots("Mon 17:00") == [], "Non-dict should yield no slots"
    print("  [PASS] None / empty / non-dict return empty list")

    assert normalize_schedule_slots({"Mon": "17:00"}) == [{"day": "Mon", "time": "17:00"}], \
        "Bare string time should be accepted"
    print("  [PASS] Bare string time coerced to single slot")

    assert normalize_schedule_slots({"Mon": ["17:00", "", "  "]}) == [{"day": "Mon", "time": "17:00"}], \
        "Blank times should be skipped"
    assert normalize_schedule_slots({"Mon": [None, 1700]}) == [], \
        "Non-string times should be skipped"
    print("  [PASS] Blank and non-string times skipped")

    assert normalize_schedule_slots({"Mon": [" 17:00 "]}) == [{"day": "Mon", "time": "17:00"}], \
        "Times should be trimmed"
    print("  [PASS] Times trimmed")


def test_normalize_dedupes_and_keeps_unknown_days():
    print("\n" + "=" * 60)
    print("TEST: Schedule normalization - dedupe and unknown days")
    print("=" * 60)

    assert normalize_schedule_slots({"Mon": ["17:00", "17:00"]}) == [{"day": "Mon", "time": "17:00"}], \
        "Duplicate day+time should collapse"
    print("  [PASS] Duplicate slots de-duplicated")

    slots = normalize_schedule_slots({"Holiday": ["09:00"], "Mon": ["17:00"]})
    assert slots == [
        {"day": "Mon", "time": "17:00"},
        {"day": "Holiday", "time": "09:00"},
    ], f"Unknown day should sort last but be kept: {slots}"
    print("  [PASS] Unknown day kept and sorted after known weekdays")


def test_schedule_schema():
    print("\n" + "=" * 60)
    print("TEST: ClassScheduleRead schema")
    print("=" * 60)

    from app.schemas.class_ import ClassScheduleRead

    model = ClassScheduleRead(
        class_id=uuid.uuid4(),
        name="Beginner A",
        level="beginner",
        teacher_name="Ms. Lan",
        slots=normalize_schedule_slots({"Mon": ["17:00"], "Wed": ["17:00"]}),
    )
    assert len(model.slots) == 2, "Both slots should survive validation"
    assert model.slots[0].day == "Mon" and model.slots[0].time == "17:00"
    print("  [PASS] Schema validates normalized slots")

    empty = ClassScheduleRead(class_id=uuid.uuid4(), name="No Schedule Yet")
    assert empty.slots == [] and empty.level is None and empty.teacher_name is None
    print("  [PASS] Schema defaults to empty slots / null level and teacher")


def test_schedule_route_mounted():
    print("\n" + "=" * 60)
    print("TEST: Schedule route mounted")
    print("=" * 60)

    from app.main import app
    routes = [route.path for route in app.routes]

    assert any(r.endswith("/{class_id}/schedule") for r in routes), \
        f"Schedule route missing. classes routes: {[r for r in routes if 'classes' in r]}"
    print("  [PASS] GET /{class_id}/schedule mounted")

    # The single-class route must not shadow the schedule route
    schedule_route = next(r for r in routes if r.endswith("/{class_id}/schedule"))
    detail_route = next(r for r in routes if r.endswith("/{class_id}"))
    assert routes.index(detail_route) != routes.index(schedule_route), "Routes must be distinct"
    print("  [PASS] Schedule route distinct from class detail route")


if __name__ == "__main__":
    test_normalize_standard_shape()
    test_normalize_tolerates_loose_input()
    test_normalize_dedupes_and_keeps_unknown_days()
    test_schedule_schema()
    test_schedule_route_mounted()
    print("\n" + "=" * 60)
    print("All CAMS-0004 schedule tests PASSED!")
    print("=" * 60)
