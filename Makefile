start:
	source env/bin/activate && python main.py

freeze:
	pip freeze > requirements.txt

install:
	pip install -r requirements.txt

generate:
	cd prisma generate

reset:
	cd prisma migrate reset

db_push:
	cd prisma db push

.PHONY: start freeze install generate reset db_push