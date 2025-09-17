from setuptools import setup, find_packages

with open("README.md", "r", encoding="utf-8") as fh:
    long_description = fh.read()

setup(
    name="speculum-principis",
    version="0.1.0",
    author="Terrence Giggy",
    description="A Python-based generative agent for monitoring public internet material",
    long_description=long_description,
    long_description_content_type="text/markdown",
    packages=find_packages(),
    classifiers=[
        "Development Status :: 3 - Alpha",
        "Intended Audience :: Developers",
        "License :: OSI Approved :: MIT License",
        "Operating System :: OS Independent",
        "Programming Language :: Python :: 3",
        "Programming Language :: Python :: 3.8",
        "Programming Language :: Python :: 3.9",
        "Programming Language :: Python :: 3.10",
        "Programming Language :: Python :: 3.11",
    ],
    python_requires=">=3.8",
    install_requires=[
        "requests>=2.31.0",
        "beautifulsoup4>=4.12.0",
        "feedparser>=6.0.10",
        "schedule>=1.2.0",
        "click>=8.1.0",
        "pydantic>=2.0.0",
        "sqlalchemy>=2.0.0",
        "python-dotenv>=1.0.0",
        "transformers>=4.30.0",
        "torch>=2.0.0",
        "nltk>=3.8.0",
        "spacy>=3.6.0",
        "aiohttp>=3.8.0",
        "asyncio-throttle>=1.0.0",
    ],
    extras_require={
        "dev": [
            "pytest>=7.4.0",
            "pytest-asyncio>=0.21.0",
            "black>=23.0.0",
            "flake8>=6.0.0",
            "mypy>=1.5.0",
        ]
    },
    entry_points={
        "console_scripts": [
            "speculum=speculum_principis.cli:main",
        ],
    },
)