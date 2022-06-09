"""
Package setup.py
"""
from pathlib import Path
import setuptools


# reading long description from file
with open("README.md", "r", encoding="utf-8") as fh:
    long_description = fh.read()

# Load packages from requirements.txt
with open(Path('./', "requirements.txt"), "r",encoding='utf-8') as file:
    REQUIREMENTS = [ln.strip() for ln in file.readlines()]

# # specify requirements of your package here
# REQUIREMENTS = ["fiona", "geopandas", "pyproj","docopt"]
# REQUIREMENTS = []

# calling the setup function
setuptools.setup(
    name="mt_ais_toolbox",
    version="0.0.1a1",
    description="A set of tool to create density maps for AIS data",
    long_description=long_description,
    long_description_content_type="text/markdown",
    # url='',
    author="MarineTraffic Research Labs",
    author_email="research@marinetraffic.com",
    license="CC BY-NC-SA 4.0",
    package_dir={"": "src"},
    packages=setuptools.find_packages(
        where="src", include=["mt", "mt.*", "mt.utils", "mt.utils.*"]
    ),
    classifiers=[
        "Development Status :: 4 - Alpha",
        "Intended Audience :: Developers",
        "Topic :: Scientific/Engineering :: GIS ",
        "License :: CC BY-NC-SA 4.0",
        "Programming Language :: Python",
        "Programming Language :: Python :: 3.8",
    ],
    install_requires=REQUIREMENTS,
    keywords="AIS density map",
    python_requires=">=3.8",

)
