# Running Vlasisku Locally with Docker

## Quick Start

1. **Build and start the container:**
   ```bash
   docker compose up -d
   ```

2. **Access the application:**
   Open your browser and navigate to: http://localhost:8080

3. **View logs:**
   ```bash
   docker compose logs -f
   ```

4. **Stop the container:**
   ```bash
   docker compose down
   ```

## Development

The docker-compose.yml is configured for development with:
- Code mounted as a volume (changes require container restart)
- Database persisted in a Docker volume
- Debug mode enabled

## Updating the Database

To update the dictionary database:
```bash
docker compose exec vlasisku flask updatedb
```

## Useful Commands

- **Rebuild the image:** `docker compose build`
- **Restart the container:** `docker compose restart`
- **View container status:** `docker compose ps`
- **Access container shell:** `docker compose exec vlasisku bash`

## Notes

- The database will be automatically downloaded on first run
- The database is stored in a Docker volume and persists between container restarts
- Port 8080 is exposed to your host machine
