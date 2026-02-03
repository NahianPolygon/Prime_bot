#!/bin/bash

set -e

PROJECT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
IMAGES_DIR="$PROJECT_DIR/graph_images"
CONTAINER_NAME="prime_bot_app"

echo "🧹 Cleaning up old graph images..."
rm -f "$IMAGES_DIR"/*.png
echo "📁 Removed all old graphs from: $IMAGES_DIR"

echo ""
echo "📋 Copying updated visualize_graphs.py to container..."
docker cp "$PROJECT_DIR/visualize_graphs.py" "$CONTAINER_NAME":/app/visualize_graphs.py

echo ""
echo "🏗️  Regenerating graphs inside container..."
docker exec "$CONTAINER_NAME" python visualize_graphs.py

echo ""
echo "📥 Copying latest graphs from container to local directory..."
docker cp "$CONTAINER_NAME":/app/graph_images/. "$IMAGES_DIR/"

echo ""
echo "✅ All done! Latest graphs are in: $IMAGES_DIR"
echo ""
echo "📊 Generated graphs:"
ls -lh "$IMAGES_DIR"/*.png | awk '{print "   - " $9}'
