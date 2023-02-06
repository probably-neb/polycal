# from ics import Calendar, Event
from uuid import uuid4
from datetime import datetime, timezone, time
from dataclasses import dataclass, field
import pathlib
from typing import Tuple, List, Dict, Any, Union, Optional, Iterator
import re

from .core import Course, Professor, Meetings, Weekday, PST

DT_RGX = re.compile(r"DT([ENDSTART]+)(:.*)Z")
DT_REPL_RGX = r"DT\1;TZID=America/Los_Angeles\2"
# BEGIN = "2023-01-01"
# END = "2023-05-01"
CRLF = "\r\n"
# copied from google calendar ics export
PST_STR = """BEGIN:VTIMEZONE
TZID:America/Los_Angeles
X-LIC-LOCATION:America/Los_Angeles
BEGIN:DAYLIGHT
TZOFFSETFROM:-0800
TZOFFSETTO:-0700
TZNAME:PDT
DTSTART:19700308T020000
RRULE:FREQ=YEARLY;BYMONTH=3;BYDAY=2SU
END:DAYLIGHT
BEGIN:STANDARD
TZOFFSETFROM:-0700
TZOFFSETTO:-0800
TZNAME:PST
DTSTART:19701101T020000
RRULE:FREQ=YEARLY;BYMONTH=11;BYDAY=1SU
END:STANDARD
END:VTIMEZONE"""


def jan_first_pst() -> datetime:
    return datetime(2023, 1, 1, tzinfo=PST)


def current_datetime_utc() -> datetime:
    return datetime.now(timezone.utc)


# copied from https://github.com/ics-py/ics-py/blob/main/src/ics/utils.py
def uid_gen() -> str:
    uid = str(uuid4())
    return f"{uid}@{uid[:4]}.org"


def encode_string(val: str) -> str:
    return val.encode("unicode_escape").decode("utf-8")


# COULDO: make this only take kw args
# so name is not str
LINE_LENGTH = 75


def fold_line(line: str) -> str:
    def line_chunks() -> Iterator[Tuple[int, str]]:
        for i, o in enumerate(range(0, len(line), LINE_LENGTH)):
            yield i, line[o : o + LINE_LENGTH]

    return CRLF.join([f"{' '*i}{chunk}" for i, chunk in line_chunks()])


def content_line(name, val=None, **kwargs):
    def fmt_assign_tuple(nv):
        return f"{nv[0]}={nv[1]}"

    if isinstance(val, dict):
        _val = val.pop("val", None) if val.get("val") else None
        kwargs |= val
        val = _val
    assigns = list(map(fmt_assign_tuple, kwargs.items()))
    if val is None:
        line = f'{name}:{";".join(assigns)}'
    else:
        line = ";".join([name, *assigns]) + ":" + str(val)
    return fold_line(line)


def content_block(name, *content):
    begin = content_line("BEGIN", name)
    end = content_line("END", name)
    content = [begin, *[c for c in content if c is not None], end]
    text = CRLF.join(content)
    # encoded_text = encode_string(text)
    return text


def format_time(dt: datetime):
    # old =  dt.isoformat(timespec='seconds').replace(
    #     '+00:00', '').replace('-', '').replace(':', '')
    new = dt.strftime("%Y%m%dT%H%M%S")
    # assert old == new, f'{old} != {new}'
    return new


def timezone_name(tz: timezone) -> str:
    return tz.tzname(None)


# TODO: make ContentBlock class
# for VCALENDAR and VEVENT with
# methods for adding lines

# COULDO: make decorator for properties
# with content line formatting logic


class IcsVal:
    def __init__(
        self,
        field_name: str = None,
        default: Any = None,
        default_factory=None,
        fmt=None,
    ):
        self._ics_name = field_name
        self._default = default
        self._default_factory = default_factory
        self.fmt = fmt

    def __class_getitem__(cls, key):
        return cls(key)

    def __set_name__(self, owner, name):
        if self._ics_name is None:
            self._ics_name = name.upper().replace("_", "-")
        self._name = "_" + name

    def get_default(self):
        if self._default_factory is not None:
            self._default = self._default_factory()
        return self._default

    def __get__(self, obj, objtype=None):
        if obj is None:
            # dataclass calls get to check if there is a default value
            # return None here however because calling default factory here
            # will only call it once, not every time a new instance
            # is created. Instead we use default in __set__ when a None val
            # is passed
            return None
        return self.ics_fmt(obj)

    def __set__(self, obj, val):
        if val is None:
            val = self.get_default()
        setattr(obj, self._name, val)

    def formatter(self, format_func):
        return type(self)(
            field_name=self._ics_name, default=self._default, fmt=format_func
        )

    def ics_fmt(self, obj) -> Optional[str]:
        if not hasattr(obj, self._name):
            raise AttributeError(f"{obj} has no attribute {self._name}")
        key = self._ics_name
        val = getattr(obj, self._name)
        if val is None:
            return None
        if self.fmt is not None:
            val = self.fmt(self=obj, val=val)
        return content_line(key, val)


def dtstamp() -> str:
    return format_time(current_datetime_utc())


def format_tz_time(val, tz=None):
    t = format_time(val)
    tzname = timezone_name(tz) if tz else None
    return dict(val=t, TZID=tzname)


@dataclass
class Event:
    def _format_tz_time(self, val):
        return format_tz_time(val, self.tz)

    summary: IcsVal[str] = IcsVal("SUMMARY")
    begin: IcsVal[datetime] = IcsVal(
        "DTSTART", default_factory=jan_first_pst, fmt=_format_tz_time
    )
    end: IcsVal[datetime] = IcsVal(
        "DTEND", default_factory=jan_first_pst, fmt=_format_tz_time
    )
    uid: IcsVal[str] = IcsVal(default_factory=uid_gen)
    dtstamp: IcsVal[str] = IcsVal("DTSTAMP", default_factory=dtstamp)
    location: IcsVal[str] = IcsVal()
    description: IcsVal[str] = IcsVal()
    rrule: IcsVal[Tuple[List[Weekday], datetime]] = IcsVal()
    tz: timezone = PST

    @description.formatter
    def description(self, val):
        _description = val.strip().encode("unicode_escape").decode("utf-8")
        return _description

    @rrule.formatter
    def rrule(self, val):
        if val is None:
            return
        days, until = val
        days = ",".join([d.ics_name for d in days])
        until = format_time(until)
        return dict(FREQ="WEEKLY", UNTIL=until, WKST="SU", BYDAY=days)

    @property
    def name(self) -> str:
        return self._summary

    @name.setter
    def name(self, name: str):
        self.summary = name

    @property
    def tz_name(self) -> str:
        return timezone_name(self.tz)

    def fmt_rrule(self) -> str:
        if self.rrule is None:
            return ""
        days: List[Weekday] = self._rrule[0]
        until: datetime = self._rrule[1]
        daystr: str = ",".join([d.ics_name for d in days])
        untilstr: str = format_time(until)
        return content_line(
            "RRULE", FREQ="WEEKLY", UNTIL=untilstr, WKST="SU", BYDAY=daystr
        )

    def serialize(self) -> str:
        lines = [
            self.summary,
            self.location,
            self.description,
            self.rrule,
            self.begin,
            self.end,
            self.dtstamp,
            self.uid,
        ]

        return content_block("VEVENT", *lines)


@dataclass
class Calendar:
    events: List[Event] = field(default_factory=list)
    prodid: IcsVal[str] = IcsVal(default="neb")
    version: IcsVal[str] = IcsVal(default="2.0")
    calscale: IcsVal[str] = IcsVal(default="GREGORIAN")
    tz: str = PST_STR

    def serialize(self) -> str:
        events = [e.serialize() for e in self.events]
        return content_block(
            "VCALENDAR", self.prodid, self.version, self.calscale, self.tz, *events
        )


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
            # print(course.name, "class:", time_)
            return datetime.combine(date=first_day, time=time_, tzinfo=PST)

        e.begin = first_class(start_time)
        e.end = first_class(end_time)
        last_class_end = datetime.combine(date=last_day, time=end_time, tzinfo=PST)
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
