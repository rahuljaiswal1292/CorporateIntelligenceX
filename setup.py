"""Setup script for UAE Corporate Intelligence Hub"""
from setuptools import setup, find_packages

with open("requirements.txt") as f:
    requirements = f.read().splitlines()

with open("README.md", "r", encoding="utf-8") as f:
    long_description = f.read()

setup(
    name="uae-corporate-intelligence-hub",
    version="1.0.0",
    author="Corporate Intelligence X Team",
    author_email="team@corporateintelligence.x",
    description="Multi-agent system for company profiling using DFM and ADX data",
    long_description=long_description,
    long_description_content_type="text/markdown",
    url="https://github.com/corporateintelligencex/uae-market-intelligence",
    packages=find_packages(),
    classifiers=[
        "Development Status :: 4 - Beta",
        "Intended Audience :: Financial and Insurance Industry",
        "License :: OSI Approved :: MIT License",
        "Operating System :: OS Independent",
        "Programming Language :: Python :: 3",
        "Programming Language :: Python :: 3.9",
        "Programming Language :: Python :: 3.10",
        "Programming Language :: Python :: 3.11",
        "Topic :: Office/Business :: Financial",
    ],
    python_requires=">=3.9",
    install_requires=requirements,
    extras_require={
        "dev": [
            "pytest>=7.0.0",
            "pytest-asyncio>=0.21.0",
            "black>=23.0.0",
            "flake8>=6.0.0",
            "mypy>=1.0.0",
        ],
    },
    entry_points={
        "console_scripts": [
            "intelligence-hub=main:main",
        ],
    },
    include_package_data=True,
    zip_safe=False,
)