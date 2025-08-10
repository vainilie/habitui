from __future__ import annotations

from setuptools import setup, find_packages


setup(
	name="habitui",
	version="0.1.0",
	packages=find_packages(where="src"),
	package_dir={"": "src"},
)
