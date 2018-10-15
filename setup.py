#!/usr/bin/env python3

from setuptools import setup, find_packages

# Get the long description from the README file
with open('README.rst', encoding='utf-8') as f:
    long_description = f.read()

setup(
    name='flask-rest-api',
    version='0.9.2',
    description='Build a REST API with Flask',
    long_description=long_description,
    url='https://github.com/Nobatek/flask-rest-api',
    author='Jérôme Lafréchoux',
    author_email='jlafrechoux@nobatek.com',
    license='MIT',
    # See https://pypi.python.org/pypi?%3Aaction=list_classifiers
    classifiers=[
        'Development Status :: 4 - Beta',
        'Intended Audience :: Developers',
        'Topic :: Internet :: WWW/HTTP',
        'Environment :: Web Environment',
        'Framework :: Flask',
        'License :: OSI Approved :: MIT License',
        'Programming Language :: Python :: 3.5',
        'Programming Language :: Python :: 3.6',
    ],
    keywords='flask REST api',
    packages=find_packages(exclude=['tests*']),
    include_package_data=True,
    package_data={
        '': ['spec/templates/*'],
    },
    install_requires=[
        'werkzeug>=0.11',
        'flask>=1.0',
        'marshmallow>=2.15.2',
        'webargs>=1.5.2',
        'apispec>=0.39.0',
    ],
)
