# Setting up PostgreSQL 17 Docker for SÚKL API Script

This guide will help you set up a PostgreSQL 17 Docker container to use with the SÚKL API script.

## Prerequisites

- Docker Desktop installed on Windows
- PowerShell

## Docker Setup Commands

1. **Pull the PostgreSQL 17 image**:

```powershell
docker pull postgres:17
```

2. **Create and run the PostgreSQL container**:

```powershell
docker run --name sukl-postgres -e POSTGRES_PASSWORD=test -e POSTGRES_USER=test -e POSTGRES_DB=test -p 5432:5432 -d postgres:17
```

This command:

- Creates a container named `sukl-postgres`
- Sets up the database with username and password both as `test`
- Creates a database named `test`
- Maps port 5432 from the container to your host machine
- Runs in detached mode (-d)

## Verify the Container is Running

```powershell
docker ps
```

You should see your `sukl-postgres` container in the list.

## Connect to PostgreSQL and Create Schema

1. **Connect to the PostgreSQL container**:

```powershell
docker exec -it sukl-postgres psql -U test
```

2. **Create the schema**:

```sql
CREATE SCHEMA test;
```

3. **Set the search path to use the schema**:

```sql
ALTER DATABASE test SET search_path TO test;
```

4. **Exit PostgreSQL**:

```sql
\q
```

## Update the Script Connection Parameters

In your `step2_sukl_api.py` script, update the DatabaseManager initialization parameters to connect to your Docker container:

```python
db_manager = DatabaseManager(
    host="your_docker_host_ip",  # Use "localhost" if running on the same machine
    port=5432,                  # Default PostgreSQL port
    database="test",            # Database name
    user="test",                # Username
    password="test"             # Password
)
```

If Docker is running on another machine, replace `host` with that machine's IP address.

## Useful Docker Commands

- **Stop the container**:

  ```powershell
  docker stop sukl-postgres
  ```

- **Start an existing container**:

  ```powershell
  docker start sukl-postgres
  ```

- **Remove the container** (will delete all data):

  ```powershell
  docker rm sukl-postgres
  ```

- **View container logs**:
  ```powershell
  docker logs sukl-postgres
  ```

## Persisting Data with Volumes (Optional)

To persist your database data even if the container is removed:

```powershell
docker run --name sukl-postgres -e POSTGRES_PASSWORD=test -e POSTGRES_USER=test -e POSTGRES_DB=test -p 5432:5432 -v postgres_data:/var/lib/postgresql/data -d postgres:17
```

This adds a volume named `postgres_data` that will store your database files.
