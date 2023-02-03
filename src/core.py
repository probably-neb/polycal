from __future__ import annotations
from typing import List, Optional, Dict
from dataclasses import dataclass
from enum import Enum
from datetime import time, timezone, timedelta
import re

PST = timezone(timedelta(hours=-8))

MEETING_RGX = re.compile(
    r'(?P<days>\w+) (?P<start>\d\d:\d\d) (?P<start_meridiem>\w\w) to (?P<end>\d\d:\d\d) (?P<end_meridiem>\w\w)')


class Weekday(Enum):
    Mon = 0
    Tues = 1
    Wed = 2
    Thurs = 3
    Fri = 4
    Sat = 5
    Sun = 6

    @property
    def ics_name(self) -> str:
        mappings = {
            Weekday.Mon: 'MO',
            Weekday.Tues: 'TU',
            Weekday.Wed: 'WE',
            Weekday.Thurs: 'TH',
            Weekday.Fri: 'FR',
            Weekday.Sat: 'SA',
            Weekday.Sun: 'SU',
        }
        return mappings[self]

    @classmethod
    def from_letter(cls, letter: str) -> Weekday:
        mappings = {
            'M': Weekday.Mon,
            'T': Weekday.Tues,
            'W': Weekday.Wed,
            'R': Weekday.Thurs,
            'F': Weekday.Fri,
            'Sa': Weekday.Sat,
            'Sn': Weekday.Sun,
        }
        return mappings[letter]

    @classmethod
    def from_letters(cls, letters: str) -> List[Weekday]:
        return list(map(Weekday.from_letter, letters))


@dataclass
class Meetings:
    days: List[Weekday]
    start: time
    end: time
    TIMEZONE = PST

    @classmethod
    def parse_time(cls, t: str, meridiem: str) -> time:
        hour, min = [int(i) for i in t.split(':')]
        if meridiem == 'PM':
            if hour != 12:
                hour += 12
        return time(hour, min, tzinfo=cls.TIMEZONE)

    @classmethod
    def from_string(cls, meetings: str) -> Meetings:
        if "Unknown" in meetings:
            return None
        else:
            matches = MEETING_RGX.match(meetings)
            groups = ["start", "start_meridiem", "end", "end_meridiem", "days"]
            st, st_m, e, e_m, day_chars = [matches.group(i) for i in groups]
            days = Weekday.from_letters(day_chars)

            # def parse_time_match(side: str) -> time:
            #     return time.fromisoformat(matches.group(side)).replace(tzinfo=PST)
            # start = parse_time_match('start')
            # end = parse_time_match('end')
            start = cls.parse_time(st, st_m)
            end = cls.parse_time(e, e_m)
            return Meetings(days, start, end)


@dataclass
class Professor:
    name: str
    email: str
    office_location: Optional[str] = None
    office_phone: Optional[str] = None

    MAPPINGS = {
        "Professor's name": "name",
        "Email": "email",
        "Office Phone": "office_phone",
        "Office Location": "office_location",
    }

    @classmethod
    def map_titles(cls, kv):
        k, v = kv
        return Professor.MAPPINGS[k], v

    @classmethod
    def from_dict(cls, attrs) -> Professor:
        mapped = dict(map(Professor.map_titles, attrs.items()))
        return Professor(**mapped)

    @classmethod
    def get_updated_faculty(cls):
        import pandas
        import requests
        url = "https://catalog.calpoly.edu/facultyandstaff/#facultystaffemeritustext"
        page = requests.get(url)
        prof_table = pandas.read_html(
            page.text, attrs={"class": "tbl_facdir"}, flavor="bs4")[0]
        return prof_table

    @classmethod
    def get_faculty_df(cls):
        import pathlib
        import pandas
        path = pathlib.Path(__file__).parent.parent / "faculty.csv"
        if not path.exists():
            df = Professor.get_updated_faculty()
            path.write_text(df.to_csv())
        else:
            df = pandas.read_csv(path)
        return df

    def position(self, faculty) -> str:
        res = faculty[faculty.NAME.str.contains(
            self.name, case=False)]
        if res.empty:
            return None
        else:
            return res.iloc[0].POSITION

    def ics_summary(self, faculty=None) -> str:
        pos = self.position(faculty) if faculty is not None else ""
        return f"""Professor: {self.name} {pos}
Email: {self.email}
Office: {self.office_location}
"""


@dataclass
class Course:
    meetings: Meetings
    name: str
    dscr: str
    prof: Dict
    title: Optional[str] = None
    units: Optional[int] = None
    room: Optional[str] = None

    def description(self, faculty=None):
        room = f": {self.room}" if self.room else ""
        return f"""{self.dscr}

{self.prof.ics_summary(faculty)}
"""

    @property
    def meets(self) -> bool:
        return self.meetings is not None
