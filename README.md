# Twitter SARA scraping and classification

This project scrapes tweets and trains simple classifiers for SARA-related cyberbullying.

## Data and samples
- Local datasets live in data/ and are ignored by git.
- A tiny, non-PII sample dataset is in samples/sample_scraped_sara_data.xlsx and is safe to commit.
- Copy .env_example to .env and fill in your credentials before running the scraper.

## Quick start
1. Create and activate a virtual environment.
2. Install dependencies from the pinned list:
	- pip install -r requirements.txt
3. Run the scraper: python scraper-python.py
4. Train models: python train_models.py
