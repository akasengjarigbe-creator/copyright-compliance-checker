# Copyright Compliance Checker

MSc project MVP scaffold for detecting images in student webpages, extracting attribution evidence, applying rule-based licence checks, and producing structured compliance reports.

## MVP order
1. HTML parser and crawler
2. Image detection
3. Attribution extraction
4. Licence knowledge base
5. Rule-based compliance engine
6. Report generator
7. LLM reasoning module
8. Hybrid decision engine

## Backend setup
```bash
cd backend
python -m venv .venv
.venv\Scripts\activate   # Windows
pip install -r requirements.txt
uvicorn app.main:app --reload
```

## Run tests
```bash
cd backend
pytest
```
