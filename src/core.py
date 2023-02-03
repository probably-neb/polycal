from __future__ import annotations
from typing import List, Optional, Dict
from dataclasses import dataclass
from enum import Enum
from datetime import time
import re

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

    @classmethod
    def from_string(cls, meetings: str) -> Meetings:
        if "Unknown" in meetings:
            return None
        else:
            matches = MEETING_RGX.match(meetings)
            days = Weekday.from_letters(matches.group('days'))
            start = time.fromisoformat(matches.group('start'))
            end = time.fromisoformat(matches.group('end'))
            return Meetings(days, start, end)


@dataclass
class Professor:
    professors_name: str
    email: str
    office_location: Optional[str] = None
    office_phone: Optional[str] = None

    MAPPINGS = {
        "Professor's name": "professors_name",
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

    def position(self, faculty):
        res = faculty[faculty.NAME.str.contains(self.professors_name, case=False)]
        if res.empty:
            return None
        else:
            return res.iloc[0].POSITION

@dataclass
class Course:
    meetings: Meetings
    name: str
    dscr: str
    prof: Dict
    units: Optional[int] = None
