#!/usr/bin/env python3

from setuptools import setup, find_packages

# Get the long description from the README file
with open('README.rst', encoding='utf-8') as f:
    long_description = f.read()

setup(
    name='flask-smorest',
    version='0.25.1',
    description='Flask/Marshmallow-based REST API framework',
    long_description=long_description,
    url='https://github.com/marshmallow-code/flask-smorest',
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
        'Programming Language :: Python :: 3.6',
        'Programming Language :: Python :: 3.7',
        'Programming Language :: Python :: 3.8',
        'Programming Language :: Python :: 3.9',
        'Programming Language :: Python :: 3 :: Only',
    ],
    keywords=[
        'REST',
        'openapi',
        'swagger',
        'flask',
        'marshmallow',
        'apispec'
        'webargs',
    ],
    packages=find_packages(exclude=['tests*']),
    include_package_data=True,
    package_data={
        '': ['spec/templates/*'],
    },
    python_requires='>=3.6',
    install_requires=[
        'werkzeug>=0.15,<2',
        'flask>=1.1.0,<2',
        'marshmallow>=3.0.0,<4',
        'webargs>=6.0.0,<7',
        'apispec>=4.0.0,<5',
    ],
)
