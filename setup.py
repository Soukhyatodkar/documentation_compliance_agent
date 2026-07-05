"""
Setup script for Documentation Compliance Agent
"""
from setuptools import setup, find_packages

setup(
    name="documentation-compliance-agent",
    version="1.0.0",
    packages=find_packages(),
    include_package_data=True,
    install_requires=[
        "python-dotenv==1.0.0",
        "pydantic==2.5.3",
        "pydantic-settings==2.1.0",
        "pyyaml==6.0.1",
        "typer==0.9.0",
        "rich==13.7.0",
        "playwright==1.40.0",
        "aiohttp==3.9.1",
        "qdrant-client==2.7.0",
        "openai==1.6.0",
        "numpy==1.24.3",
        "pypdf==3.17.1",
        "PyPDF2==3.0.1",
        "pdfplumber==0.10.3",
        "pandas==2.1.3",
        "structlog==23.3.0",
        "pytest==7.4.3",
        "requests==2.31.0",
        "tenacity==8.2.3",
    ],
    extras_require={
        "dev": [
            "black==23.12.0",
            "flake8==6.1.0",
            "isort==5.13.2",
            "mypy==1.7.1",
            "pylint==3.0.3",
        ]
    },
    entry_points={
        "console_scripts": [
            "compliance-agent=src.main:app",
        ],
    },
    python_requires=">=3.11",
    author="Documentation Compliance Team",
    description="Automated compliance checking for web applications against documentation",
    long_description=open("README.md").read(),
    long_description_content_type="text/markdown",
    url="https://github.com/example/documentation-compliance-agent",
    classifiers=[
        "Development Status :: 4 - Beta",
        "Intended Audience :: Developers",
        "License :: OSI Approved :: MIT License",
        "Programming Language :: Python :: 3.11",
        "Programming Language :: Python :: 3.12",
    ],
)
