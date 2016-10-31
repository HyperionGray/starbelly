import os


def get_path(relpath):
    ''' Return absolute path for given path relative to project root. '''

    base_dir = os.path.dirname(os.path.dirname(__file__))
    return os.path.abspath(os.path.join(base_dir, relpath))
