# SÚKL API PostgreSQL Setup

This repository contains scripts to set up a PostgreSQL 17 Docker container for use with the SÚKL API data collection script.

## Files

- `setup_postgres_docker.md` - Detailed instructions for setting up PostgreSQL 17 in Docker
- `docker-compose.yml` - Docker Compose configuration for PostgreSQL
- `setup_postgres.bat` - Windows batch script to automate the setup process
- `step2_sukl_api.py` - SÚKL API data collection script

## Quick Start

1. Make sure Docker Desktop is installed and running on your Windows machine
2. Run the setup script:
   ```
   setup_postgres.bat
   ```
3. The script will:
   - Pull the PostgreSQL 17 Docker image
   - Create and start a container named `sukl-postgres`
   - Create the necessary schema
   - Display connection details

## Manual Setup

If you prefer to set up manually or need more control, follow the instructions in `setup_postgres_docker.md`.

## Using with SÚKL API Script

The PostgreSQL container is configured with:

- Database name: `test`
- Username: `test`
- Password: `test`
- Port: `5432`
- Schema: `test`

These are the default values in the `step2_sukl_api.py` script, so it should work without modification if running on the same machine.

If running the script from a different machine, update the `host` parameter in the `DatabaseManager` initialization.

## Troubleshooting

- **Port conflict**: If port 5432 is already in use, modify the port mapping in `docker-compose.yml`
- **Connection issues**: Ensure Docker is running and the container is healthy with `docker ps`
- **Schema issues**: Connect to the database with `docker exec -it sukl-postgres psql -U test` and verify the schema exists
