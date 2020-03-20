#!/usr/bin/env python3

from setuptools import setup, find_packages

# Get the long description from the README file
with open('README.rst', encoding='utf-8') as f:
    long_description = f.read()

setup(
    name='flask-smorest',
    version='0.20.0',
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
        'Programming Language :: Python :: 3.5',
        'Programming Language :: Python :: 3.6',
        'Programming Language :: Python :: 3.7',
        'Programming Language :: Python :: 3.8',
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
    python_requires='>=3.5',
    install_requires=[
        'werkzeug>=0.15',
        'flask>=1.1.0',
        'marshmallow>=2.15.2',
        'webargs>=1.5.2,<6.0.0',
        'apispec>=3.0.0',
    ],
)
