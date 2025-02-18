from setuptools import setup, find_packages

setup(
    name="good",
    version="0.1",
    packages=find_packages(),
    install_requires=[
        "numpy>=1.21.0",
        "scipy>=1.7.0",
        "pyomo>=6.4.0",
        "networkx>=2.6.0",
        "pandas>=1.3.0",
        "highspy>=1.5.0",
    ],
) 