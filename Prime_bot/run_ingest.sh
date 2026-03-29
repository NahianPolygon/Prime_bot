#!/bin/bash

CONTAINER="primebot-api"

if [ "$(docker ps -q -f name=$CONTAINER)" ]; then
    echo "Running ingestion inside $CONTAINER..."
    docker exec -it $CONTAINER python -m ingestion.ingest $@
    echo "Done."
else
    echo "Container $CONTAINER is not running. Start it first with: docker compose up -d"
fi
