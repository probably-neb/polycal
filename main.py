from src import parser, ics
import pathlib

with open('./my_classes.html', 'r') as f:
    courses = parser.parse(f.read())
from pprint import pprint
pprint(courses)
# for course in courses:
#     print(course.ics_summary())

cal = ics.create_calendar(courses)
# print(cal)

cal_path = pathlib.Path('./calendar.ics')
cal_path.write_text(cal.serialize())
