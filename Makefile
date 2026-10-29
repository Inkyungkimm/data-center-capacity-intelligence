.PHONY: start ingest build dashboard test
start:
	docker compose up -d
ingest:
	python -m capacity_intelligence.ingest --download --max-files 1 --max-requests 20000
build:
	cd dbt_project && dbt build
dashboard:
	streamlit run dashboard/app.py
test:
	pytest -q
