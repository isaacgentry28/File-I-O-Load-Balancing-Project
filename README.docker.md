Local Docker demo

This compose setup runs two server containers and an nginx load balancer (round-robin) in front of them.

Structure and intent
- server/: the FastAPI application (container image built from `server/Dockerfile`)
- repo_data/: host directory to be bind-mounted into containers for shared file storage
- server_config.json: copied into containers read-only to provide api_key and repo_root
- nginx: simple reverse proxy that round-robins requests to server1 and server2

Run locally
1. Ensure Docker and docker-compose are installed.
2. From repository root:

   docker compose build
   docker compose up

3. The load-balanced service will be available at http://localhost:8000

Verify
- Health:
  curl http://localhost:8000/health

- Upload a file (use a path with no leading `/`):
  curl -X POST -H "x-api-key: dev-key-123" -F "file=@/path/to/localfile" http://localhost:8000/files/test/file.bin

- Download:
  curl -H "x-api-key: dev-key-123" http://localhost:8000/files/test/file.bin -o out.bin

Caveats
- The app's in-process locks do NOT coordinate across containers. For concurrent writes to the same path you should add distributed locking (Redis, etc.) or centralize write routing.
- This demo uses a shared host directory `repo_data/` mounted into both containers to simulate shared storage.

Next steps (optional)
- Add Redis and implement distributed locking in the app.
- Add TLS termination in nginx.
- Use real storage volumes for production.
