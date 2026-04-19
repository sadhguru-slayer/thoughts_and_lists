# To run migrations and upgrade head in alembic I use:
1. docker compose -f docker-compose.dev.yaml exec --workdir // app alembic revision --autogenerate -m "wtevr"
2. docker compose -f docker-compose.dev.yaml exec --workdir // app alembic upgrade head

## Also: 
docker compose -f docker-compose.dev.yaml exec -c app alembic current  (Shows current DB revision)
docker compose -f docker-compose.dev.yaml exec -c app alembic history  (Shows all migrations)

## To run Docker:
Simply use - docker-compose up --build