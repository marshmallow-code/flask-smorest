#!/usr/bin/env python3

from setuptools import setup, find_packages

# Get the long description from the README file
with open('README.rst', encoding='utf-8') as f:
    long_description = f.read()

setup(
    name='flask-smorest',
    version='0.34.0',
    description='Flask/Marshmallow-based REST API framework',
    long_description=long_description,
    url='https://github.com/marshmallow-code/flask-smorest',
    author='Jérôme Lafréchoux',
    author_email='jerome@jolimont.fr',
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
        'werkzeug>=2.0,<3',
        'flask>=2.0,<3',
        'marshmallow>=3.13.0,<4',
        'webargs>=8.0.0,<9',
        'apispec>=5.1.0,<6',
    ],
)
