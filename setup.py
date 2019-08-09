"""
Copyright (c) 2019 ETH Zurich
This Source Code Form is subject to the terms of the Mozilla Public
License, v. 2.0. If a copy of the MPL was not distributed with this
file, You can obtain one at http://mozilla.org/MPL/2.0/.
"""

from setuptools import setup, find_packages


setup(
    name='2vyper',
    version='0.0.1',
    license='MPL-2.0',

    packages=find_packages('src'),
    package_dir={'': 'src'},
    package_data={
        'nagini_translation.backends': ['*.jar'],
        'nagini_translation.resources': ['*.vpr'],
    },
    install_requires=[
        'astunparse==1.6.2',
        'jpype1==0.7.0',
        'vyper',
        'z3-solver',
    ],
    tests_require=[
        'pytest>=3.3.0'
    ],
    entry_points={
        'console_scripts': [
                '2vyper = nagini_translation.main:main',
        ]
    },

    author='Viper Team',
    author_email='viper@inf.ethz.ch',
    url='http://www.pm.inf.ethz.ch/research/nagini.html',
    description='Static verifier for Vyper, based on Viper.',
    long_description=(open('README.rst').read()),
    # Full list of classifiers could be found at:
    # http://pypi.python.org/pypi?%3Aaction=list_classifiers
    classifiers=[
        'Development Status :: 3 - Alpha',
        'Environment :: Console',
        'Intended Audience :: Developers',
        'License :: OSI Approved :: Mozilla Public License 2.0 (MPL 2.0)',
        'Operating System :: OS Independent',
        'Programming Language :: Python :: 3 :: Only',
        'Topic :: Software Development',
    ],
)
