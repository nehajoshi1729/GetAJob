# GetHired – Job Aggregator

GetHired is a Python-based job aggregator that searches for job postings across multiple job boards using Google search queries. The script extracts job details from the resulting pages and filters them based on customizable criteria such as job type and recency. Additionally, it can compare job descriptions to find similar positions using spaCy's text similarity features.

---

## Table of Contents

- [Features](#features)
- [Requirements](#requirements)
- [Installation](#installation)
- [Usage](#usage)
- [Customization](#customization)
- [Troubleshooting](#troubleshooting)
- [License](#license)
- [Acknowledgments](#acknowledgments)

---

## Features

- **Query Construction:**  
  Constructs domain-specific Google search queries to target various job boards.

- **HTML Parsing:**  
  Uses BeautifulSoup to extract job details (title, company, date, description, and URL) from web pages.

- **Recency Filtering:**  
  Filters job postings based on a user-defined recency threshold. Job postings without a date are considered valid.

- **Job Similarity:**  
  Compares job descriptions using spaCy to suggest similar job postings.

- **Customizable:**  
  Easily update search queries, HTML selectors, and similarity thresholds to match your needs.

---

## Requirements

- **Python:** 3.7 or higher
- **Packages:**
  - [requests](https://pypi.org/project/requests/)
  - [beautifulsoup4](https://pypi.org/project/beautifulsoup4/)
  - [googlesearch-python](https://pypi.org/project/googlesearch-python/)
  - [spacy](https://pypi.org/project/spacy/)
- **spaCy English Model:** `en_core_web_md`

---


