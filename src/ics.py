from ics import Calendar, Event
from ics.grammar.parse import ContentLine
from datetime import datetime, timezone

from typing import List, Optional
from .core import Course, Professor, Meetings, Weekday
BEGIN = "2023-01-01"
END = "2023-05-01"


def add_rrule(e: Event, days: List[Weekday]):
    days = ','.join([d.ics_name for d in days])
    e.extra.append(ContentLine(
        name='RRULE', value=f'FREQ=WEEKLY;WKST=SU;BYDAY={days}'))


def create_event(course: Course) -> Event:
    e = Event()
    e.name = course.name
    if course.meets:
        e.begin = BEGIN + 'T'+course.meetings.start.isoformat()
        e.end = BEGIN + 'T'+course.meetings.end.isoformat()
        add_rrule(e, course.meetings.days)
    else:
        e.begin = BEGIN
        # e.end = END
        # e.make_all_day()
    time_now = datetime.now(timezone.utc).isoformat(timespec='seconds').replace(
        '+00:00', '').replace('-', '').replace(':', '')
    e.extra.append(ContentLine(name='DTSTAMP', value=time_now))
    e.description = course.description()
    e.location = course.room
    return e


def create_calendar(courses: List[Course]) -> Calendar:
    cal = Calendar()
    for course in courses:
        cal.events.add(create_event(course))

    return cal
