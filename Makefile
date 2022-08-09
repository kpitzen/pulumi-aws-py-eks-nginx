
up:
	poetry run pulumi up

preview:
	poetry run pulumi preview

format:
	poetry run black .
	poetry run isort .