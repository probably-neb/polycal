# from ics import Calendar, Event
from uuid import uuid4
from ics.grammar.parse import ContentLine
from datetime import datetime, timezone, time
from dataclasses import dataclass, field
import pathlib
from typing import *
import re

from .core import Course, Professor, Meetings, Weekday, PST

DT_RGX = re.compile(r'DT([ENDSTART]+)(:.*)Z')
DT_REPL_RGX = r'DT\1;TZID=America/Los_Angeles\2'
# BEGIN = "2023-01-01"
# END = "2023-05-01"


def jan_first_pst() -> datetime:
    return datetime(2023, 1, 1, tzinfo=PST)


def current_datetime_utc() -> datetime:
    return datetime.now(timezone.utc)


def uid_gen() -> str:
    return str(uuid4())


# COULDO: make this only take kw args
# so name is not str
def content_line(name, val="", **kwargs):
    def fmt_assign_tuple(nv): return f'{nv[0]}={nv[1]}'
    assigns = list(map(fmt_assign_tuple, kwargs.items()))
    val = f':{val}' if val else ''
    return ';'.join([name, *assigns]) + val


def format_time(dt: datetime):
    # old =  dt.isoformat(timespec='seconds').replace(
    #     '+00:00', '').replace('-', '').replace(':', '')
    new = dt.strftime('%Y%m%dT%H%M%S')
    # assert old == new, f'{old} != {new}'
    return new


def timezone_name(tz: timezone) -> str:
    return tz.tzname(None)

# TODO: make ContentBlock class
# for VCALENDAR and VEVENT with
# methods for adding lines

# COULDO: make decorator for properties
# with content line formatting logic

@dataclass
class Event:
    summary: str = ""
    begin: datetime = field(default_factory=jan_first_pst)
    end: datetime = field(default_factory=jan_first_pst)
    uid: str = field(default_factory=uid_gen)
    tz: timezone = PST
    location: Optional[str] = None
    description: Optional[str] = None
    rrule: Optional[Tuple[List[Weekday], datetime]] = None
    # _serialized: Optional[str] = field(default=None, init=False)

    @property
    def name(self) -> str:
        return self.summary

    @name.setter
    def name(self, name: str):
        self.summary = name

    @property
    def tz_name(self) -> str:
        return timezone_name(self.tz)

    def dtstamp(self) -> str:
        return format_time(current_datetime_utc())

    def fmt_rrule(self) -> str:
        if self.rrule is None:
            return ""
        days, until = self.rrule
        days = ','.join([d.ics_name for d in days])
        until = format_time(until)
        return content_line(
            'RRULE', FREQ="WEEKLY", UNTIL=until, WKST='SU', BYDAY=days).replace(";",":",1)

    def serialize(self) -> str:
        lines = []
        lines.append(content_line("BEGIN", "VEVENT"))
        lines.append(content_line("SUMMARY", self.summary))
        lines.append(content_line("LOCATION", self.location))
        description = self.description.strip().encode("unicode_escape").decode('utf-8')
        lines.append(content_line("DESCRIPTION", description))
        if (rrule := self.fmt_rrule()):
            lines.append(rrule)
        dtstart, dtend = [format_time(t) for t in [self.begin, self.end]]
        tz = self.tz_name
        lines.append(content_line("DTSTART", dtstart, TZID=tz))
        lines.append(content_line("DTEND", dtend, TZID=tz))

        lines.append(content_line("DTSTAMP", self.dtstamp()))
        lines.append(content_line("UID", self.uid))

        lines.append(content_line("END", "VEVENT"))
        return '\n'.join(lines)


@dataclass
class Calendar:
    events: List[Event] = field(default_factory=list)

    def serialize(self) -> str:
        lines = []
        lines.append(content_line("BEGIN", "VCALENDAR"))
        lines.append(content_line("PRODID","neb"))
        lines.append(content_line("VERSION", 2.0))
        for event in self.events:
            lines.append(event.serialize())
        lines.append(content_line("END", "VCALENDAR"))
        return '\n'.join(lines)


def create_course_event(course: Course) -> Event:
    e = Event()
    e.name = course.name
    first_day, last_day = course.quarter.classes_dates
    if course.has_meetings:
        start_time, end_time = course.meetings.start, course.meetings.end
        # FIXME: figure out first day of week of class and offset
        # first_day by that many days (min(course.days))
        # so first day of classes does not contain all classes

        def first_class(time_: time):
            print(course.name, "class:", time_)
            return datetime.combine(date=first_day, time=time_, tzinfo=PST)
        e.begin = first_class(start_time)
        e.end = first_class(end_time)
        last_class_end = datetime.combine(
            date=last_day, time=end_time, tzinfo=PST)
        e.rrule = (course.meetings.days, last_class_end)
    else:
        e.begin = first_day
        # TODO: how to handle classes without meetings
    time_now = format_time(datetime.now(timezone.utc))
    e.description = course.description()
    e.location = course.room
    return e


def create_calendar(courses: List[Course]) -> Calendar:
    cal = Calendar()
    for course in courses:
        event = create_course_event(course)
        cal.events.append(event)

    return cal


def save_calendar(cal: Calendar, filename: pathlib.Path):
    contents = cal.serialize()
    filename.write_text(contents)
