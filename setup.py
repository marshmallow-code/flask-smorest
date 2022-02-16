#!/usr/bin/env python3

from setuptools import setup, find_packages

EXTRAS_REQUIRE = {
    "tests": [
        "pytest==7.0.1",
        "pytest-cov==3.0.0",
        "coverage==6.3.1",
        "werkzeug==2.0.3",
        "flask==2.0.3",
        "marshmallow==3.14.1",
        "webargs==8.1.0",
        "apispec==5.1.1",
    ],
    "lint": [
        "flake8==4.0.1",
        "flake8-bugbear==22.1.11",
        "pre-commit==2.17.0",
    ],
}
EXTRAS_REQUIRE["dev"] = EXTRAS_REQUIRE["tests"] + EXTRAS_REQUIRE["lint"]


# Get the long description from the README file
with open("README.rst", encoding="utf-8") as f:
    long_description = f.read()

setup(
    name="flask-smorest",
    version="0.37.0",
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
        "Programming Language :: Python :: 3.7",
        "Programming Language :: Python :: 3.8",
        "Programming Language :: Python :: 3.9",
        "Programming Language :: Python :: 3.10",
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
    python_requires=">=3.7",
    install_requires=[
        "werkzeug>=2.0,<3",
        "flask>=2.0,<3",
        "marshmallow>=3.13.0,<4",
        "webargs>=8.0.0,<9",
        "apispec[marshmallow]>=5.1.0,<6",
    ],
    extras_require=EXTRAS_REQUIRE,
)
