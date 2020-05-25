#!/usr/bin/env python
# -*- coding: utf-8 -*-


try:
    from setuptools import setup
except ImportError:
    from distutils.core import setup


with open('README.rst') as readme_file:
    readme = readme_file.read()

requirements = [
    'pyyaml>=5.1',
    'python-daemon',
    'paho-mqtt>=1.1',
    'pyserial>=3',
    'pid>=2'
]

test_requirements = [
    'mock',
    'fixtures'
    # TODO: put package test requirements here
]

test_requirements.extend(requirements)

setup(
    name='arwn',
    version='2.0.0',
    description="Collect 433Mhz weather sensor data and publish to mqtt",
    long_description=readme,
    author="Sean Dague",
    author_email='sean@dague.net',
    url='https://github.com/sdague/arwn',
    packages=['arwn', 'arwn.cmd', 'arwn.vendor', 'arwn.vendor.RFXtrx'],
    package_dir={
        'arwn': 'arwn',
    },
    scripts=['bin/arwn-collect'],
    include_package_data=True,
    install_requires=requirements,
    license="Apache 2",
    zip_safe=False,
    keywords='arwn',
    classifiers=[
        'Development Status :: 4 - Beta',
        'Intended Audience :: Developers',
        'License :: OSI Approved :: Apache Software License',
        'Natural Language :: English',
        'Programming Language :: Python :: 3',
        'Programming Language :: Python :: 3.5',
        'Programming Language :: Python :: 3.6',
        'Programming Language :: Python :: 3.7',
        'Programming Language :: Python :: 3.8',
    ],
    test_suite='tests',
    tests_require=test_requirements
)
