#!/usr/bin/env python3

from setuptools import setup, find_packages

EXTRAS_REQUIRE = {
    "tests": [
        "pytest==7.3.1",
        "pytest-cov==4.1.0",
        "coverage==7.2.6",
        "werkzeug==2.3.4",
        "flask==2.3.2",
        "marshmallow==3.19.0",
        "webargs==8.2.0",
        "apispec==6.3.0",
        "PyYAML==6.0",
    ],
    "lint": [
        "flake8==6.0.0",
        "flake8-bugbear==23.5.9",
        "pre-commit==3.3.2",
    ],
}
EXTRAS_REQUIRE["dev"] = EXTRAS_REQUIRE["tests"] + EXTRAS_REQUIRE["lint"]


# Get the long description from the README file
with open("README.rst", encoding="utf-8") as f:
    long_description = f.read()

setup(
    name="flask-smorest",
    version="0.42.0",
    description="Flask/Marshmallow-based REST API framework",
    long_description=long_description,
    url="https://github.com/marshmallow-code/flask-smorest",
    author="Jérôme Lafréchoux",
    author_email="jerome@jolimont.fr",
    license="MIT",
    # See https://pypi.python.org/pypi?%3Aaction=list_classifiers
    classifiers=[
        "Development Status :: 4 - Beta",
        "Intended Audience :: Developers",
        "Topic :: Internet :: WWW/HTTP",
        "Environment :: Web Environment",
        "Framework :: Flask",
        "License :: OSI Approved :: MIT License",
        "Programming Language :: Python :: 3.8",
        "Programming Language :: Python :: 3.9",
        "Programming Language :: Python :: 3.10",
        "Programming Language :: Python :: 3.11",
        "Programming Language :: Python :: 3 :: Only",
    ],
    keywords=[
        "REST",
        "openapi",
        "swagger",
        "flask",
        "marshmallow",
        "apispec",
        "webargs",
    ],
    packages=find_packages(exclude=["tests*"]),
    include_package_data=True,
    package_data={
        "": ["spec/templates/*"],
    },
    python_requires=">=3.8",
    install_requires=[
        "werkzeug>=2.0.1,<3",
        "flask>=2.0,<3",
        "marshmallow>=3.18.0,<4",
        "webargs>=8.0.0,<9",
        "apispec[marshmallow]>=6.0.0,<7",
    ],
    extras_require=EXTRAS_REQUIRE,
)
