# To run migrations and upgrade head in alembic I use:
1. docker compose exec app alembic revision --autogenerate -m "add enum, ordering, unique constraint"
2. docker compose exec app alembic upgrade head

## Also: 
docker compose exec app alembic current  (Shows current DB revision)
docker compose exec app alembic history  (Shows all migrations)

## To run Docker:
Simply use - docker-compose up --build