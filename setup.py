#!/usr/bin/env python3
from setuptools import setup, find_packages

setup(
    name="folly",
    version="0.1.0",
    description="A tool for testing prompt injection and jailbreaking attacks against LLMs",
    author="JamesS",
    packages=find_packages(),
    include_package_data=True,
    package_data={
        "Folly": [
            "static/css/*.css",
            "static/js/*.js",
            "templates/*.html"
        ]
    },
    python_requires=">=3.7",
    install_requires=[
        "flask>=2.0.0",
        "flask-wtf>=1.0.0",
        "flask-session>=0.4.0",
        "requests>=2.25.0",
        "openai>=1.0.0",
        "fuzzywuzzy>=0.18.0",
        "python-Levenshtein>=0.12.0",  # For better performance with fuzzywuzzy
        "wtforms>=3.0.0",
        "gunicorn>=20.1.0",  # For production deployments
    ],
    entry_points={
        "console_scripts": [
            "folly-api=Folly.api:main",
            "folly-ui=Folly.ui_app:main",
        ],
    },
    classifiers=[
        "Development Status :: 4 - Beta",
        "Environment :: Web Environment",
        "Framework :: Flask",
        "Intended Audience :: Developers",
        "Intended Audience :: Information Technology",
        "License :: OSI Approved :: MIT License",
        "Programming Language :: Python :: 3",
        "Topic :: Security",
    ],
)
