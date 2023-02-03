import bs4
from typing import List
import re

from .core import Course, Professor, Meetings

UNITS_RGX = re.compile(r'Units: (?P<units>\d)')

def parse(html: str) -> List[Course]:
    soup = bs4.BeautifulSoup(html, 'html.parser')
    term_classes = soup.find(class_="termClasses")
    class_list_soup = term_classes \
        .find_next() \
        .find_next() \
        .find_all(class_="classView")
    courses = []
    for class_soup in class_list_soup:
        def find_text(key):
            return class_soup.find(class_=key).text.strip()
        name = find_text("classTitle")
        dscr = find_text("description")
        meetings_str = find_text("meetings")
        meetings = Meetings.from_string(meetings_str)
        class_info_soup = class_soup.find(class_="classInfoContent")
        info = {}
        for attr in class_info_soup.children:
            contents = attr.text.strip()
            if (classes := attr.get("class")):
                if "instructorContainer" in classes:
                    continue
                elif "classTitle" in classes:
                    info['title'] = contents
            else:
                if (match := UNITS_RGX.match(contents)):
                    info['units'] = match.group('units')
                else:
                    info['room'] = contents
        instructor_info_soup = class_info_soup.find(
            class_="instructorContainer")
        prof_dict = {}
        for attr in instructor_info_soup.children:
            title = attr['title']
            content = attr.span.text
            prof_dict[title] = content

        prof = Professor.from_dict(prof_dict)
        courses.append(Course(name=name, dscr=dscr,
                       meetings=meetings, prof=prof, **info))
    return courses
