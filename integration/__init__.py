'''
This module contains integration tests.

These tests rely on a RethinkDB server running on localhost 28015.
'''
import pathlib
import sys

# Add starbelly package to the path. Not sure how to do this with pipenv
# instead?
pkg = pathlib.Path(__file__).parent.parent
sys.path.append(str(pkg))
