# -*- coding: utf-8 -*-

"""setup.py: setuptools control."""
"""
A Lot of this methodology was "borrowed" from
    - https://github.com/jgehrcke/python-cmdline-bootstrap/blob/master/bootstrap/bootstrap.py
"""

import re
from setuptools import setup

install_requires = [
    'shapely', 'matplotlib', 'argparse', 'numpy'
]

version = re.search(
      '^__version__\s*=\s*"(.*)"',
      open('rivertools/__version__.py').read(),
      re.M
).group(1)

with open("README.md", "rb") as f:
      long_descr = f.read().decode("utf-8")

setup(
      name='rivertools',
      description='River tools: Centerline and Cross Sections',
      url='https://github.com/RBTDevelopmentGroup/rivertools',
      author='Matt Reimer',
      author_email='matt@northarrowresearch.com',
      license='MIT',
      packages=['rivertools'],
      zip_safe=False,
      install_requires=install_requires,
      entry_points={
            "console_scripts": ['centerline = rivertools.centerline:main',
                                'crosssections = rivertools.centerline:main']
      },
      version=version,
      long_description=long_descr,
)