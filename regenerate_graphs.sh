#!/bin/bash

# Script to regenerate and update all LangGraph visualizations
# Usage: ./regenerate_graphs.sh

set -e

PROJECT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
IMAGES_DIR="$PROJECT_DIR/graph_images"
CONTAINER_NAME="prime_bot_app"

echo "🧹 Cleaning up old graph images..."
rm -f "$IMAGES_DIR"/*.png
echo "📁 Removed all old graphs from: $IMAGES_DIR"

echo ""
echo "🏗️  Regenerating graphs inside container..."
docker exec "$CONTAINER_NAME" python visualize_graphs.py

echo ""
echo "📥 Copying latest graphs from container..."
# First clear the container's graph_images to get only latest
docker exec "$CONTAINER_NAME" bash -c "rm -f /app/graph_images/*.png"
docker exec "$CONTAINER_NAME" python visualize_graphs.py
docker cp "$CONTAINER_NAME":/app/graph_images/. "$IMAGES_DIR/" 2>&1

echo ""
echo "✅ All done! Latest graphs are in: $IMAGES_DIR"
echo ""
echo "📊 Generated graphs:"
ls -lh "$IMAGES_DIR"/*.png | awk '{print "   - " $9}'
echo ""
echo "💡 Tip: Open view_graphs.html in your browser to visualize all graphs"
