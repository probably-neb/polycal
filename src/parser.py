import bs4
from typing import List

from .core import Course, Professor, Meetings, Weekday


def parse(html: str) -> List[Course]:
    faculty = Professor.get_faculty_df()
    soup = bs4.BeautifulSoup(html, 'html.parser')
    term_classes = soup.find(class_="termClasses")
    class_list_soup = term_classes.find_next().find_next().find_all(class_="classView")
    courses = []
    for class_soup in class_list_soup:
        name = class_soup.find(class_="classTitle").text.strip()
        dscr = class_soup.find(class_="description").text.strip()
        meetings_str = class_soup.find(class_="meetings").text.strip()
        meetings = Meetings.from_string(meetings_str)
        class_info_soup = class_soup.find(class_="classInfoContent")
        instructor_info_soup = class_info_soup.find(
            class_="instructorContainer")
        # if instructor_info_soup is
        prof_dict = {}
        for attr in instructor_info_soup.children:
            title = attr['title']
            content = attr.span.text
            prof_dict[title] = content
        prof = Professor.from_dict(prof_dict)
        courses.append(Course(name=name, dscr=dscr, meetings=meetings, prof=prof))
    return courses
