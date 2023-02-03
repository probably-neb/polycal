from src import parser

with open('./my_classes.html','r') as f:
    courses = parser.parse(f.read())
from pprint import pprint
pprint(courses)
