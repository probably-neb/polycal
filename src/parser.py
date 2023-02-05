import bs4
from typing import List, Dict
import re

from .core import Course, Professor, Meetings, Quarter

UNITS_RGX = re.compile(r'Units: (?P<units>\d)')

# TODO: move get_faculty here


def get_quarters() -> Dict[str, Quarter]:
    import requests
    url = "https://registrar.calpoly.edu/academic-calendar"
    page = requests.get(url)
    soup = bs4.BeautifulSoup(page.text, 'html.parser')

    def quarter_table(id):
        return "TERM" in id

    quarter_tables = soup.find_all("table", id=quarter_table)

    def to_quarter(q_soup) -> Quarter:
        caption = q_soup.caption.text
        html = str(q_soup)
        q = Quarter.from_html(caption, html)
        return q.term, q
    quarters = dict(map(to_quarter, quarter_tables))

    return quarters


def parse_course(class_soup, quarter) -> Course:
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
    return Course(name=name, dscr=dscr,
                  meetings=meetings, prof=prof, quarter=quarter, **info)


def parse(html: str) -> List[Course]:
    soup = bs4.BeautifulSoup(html, 'html.parser')
    term_classes = soup.find(class_="termClasses")
    class_list_soup = term_classes \
        .find_next() \
        .find_next() \
        .find_all(class_="classView")
    courses = []
    quarter = get_quarters()['winter']
    for class_soup in class_list_soup:
        course = parse_course(class_soup, quarter=quarter)
        courses.append(course)
    return courses
