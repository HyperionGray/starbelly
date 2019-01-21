'''
As an application, this Starbelly package isn't intended to be published to
PyPI. This setup.py exists so that we can easily add Starbelly to the Python
path.
'''
from setuptools import setup, find_packages
from pathlib import Path

here = Path(__file__).parent

# Get version
version = {}
with (here / "starbelly" / "version.py").open() as f:
    exec(f.read(), version)

setup(
    name='starbelly',
    version=version['__version__'],
    description='Web crawler written on Trio async framework',
    url='https://github.com/HyperionGray/starbelly',
    author='Mark E. Haase',
    author_email='mhaase@hyperiongray.com',
    python_requires=">=3.7",
    keywords='web crawler',
    packages=find_packages(exclude=['docs', 'integration', 'starbelly', 'tests',
        'tools']),
    project_urls={
        'Bug Reports': 'https://github.com/HyperionGray/starbelly/issues',
        'Source': 'https://github.com/HyperionGray/starbelly',
    },
)
