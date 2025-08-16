@echo off
echo Setting up PostgreSQL 17 Docker container for SUKL API script...

REM Check if Docker is running
docker info > nul 2>&1
if %ERRORLEVEL% neq 0 (
    echo Docker is not running! Please start Docker Desktop and try again.
    exit /b 1
)

REM Pull the PostgreSQL image
echo Pulling PostgreSQL 17 image...
docker pull postgres:17

REM Check if the container already exists
docker ps -a --filter "name=sukl-postgres" --format "{{.Names}}" | findstr /i "sukl-postgres" > nul
if %ERRORLEVEL% equ 0 (
    echo Container sukl-postgres already exists.
    
    REM Check if it's running
    docker ps --filter "name=sukl-postgres" --format "{{.Names}}" | findstr /i "sukl-postgres" > nul
    if %ERRORLEVEL% equ 0 (
        echo Container is already running.
    ) else (
        echo Starting existing container...
        docker start sukl-postgres
    )
) else (
    echo Creating and starting PostgreSQL container...
    docker-compose up -d
)

echo Waiting for PostgreSQL to be ready...
timeout /t 5 /nobreak > nul

REM Create schema
echo Creating schema test...
docker exec -it sukl-postgres psql -U test -c "CREATE SCHEMA IF NOT EXISTS test;"
docker exec -it sukl-postgres psql -U test -c "ALTER DATABASE test SET search_path TO test;"

echo.
echo PostgreSQL setup complete!
echo.
echo Connection details:
echo   Host: localhost
echo   Port: 5432
echo   Database: test
echo   Username: test
echo   Password: test
echo   Schema: test
echo.
echo You can now run your SUKL API script.
