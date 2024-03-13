start:
	source env/bin/activate && python main.py

freeze:
	pip freeze > requirements.txt

install:
	pip install -r requirements.txt

generate:
	prisma generate

reset:
	prisma migrate reset

db_push:
	prisma db push

.PHONY: start freeze install generate reset db_push