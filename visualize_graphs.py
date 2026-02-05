#!/usr/bin/env python3

import sys
import logging
from pathlib import Path
from datetime import datetime

project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

from app.core.graphs.conversation_manager import ConversationManagerGraph
from app.core.graphs.product_retrieval import ProductRetrievalGraph
from app.core.graphs.comparison import ComparisonGraph
from app.core.graphs.configs import DEPOSIT_ACCOUNTS_CONFIG

# Setup logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Create graph_images directory
IMAGES_DIR = Path(__file__).parent / "graph_images"
IMAGES_DIR.mkdir(exist_ok=True)


def visualize_graph(graph_instance, graph_name: str):
    """
    Visualize a LangGraph instance and save as PNG.
    Follows the pattern: Primary PNG export with Mermaid text fallback.
    
    Args:
        graph_instance: The graph object with build_graph() method
        graph_name: Name of the graph for the output filename
    """
    try:
        logger.info(f"🎨 Visualizing {graph_name}...")
        
        # Build the graph
        compiled_graph = graph_instance.build_graph()
        
        safe_name = graph_name.lower().replace(" ", "_")
        image_path = IMAGES_DIR / f"{safe_name}.png"
        
        # Try to generate PNG using Mermaid
        try:
            png_data = compiled_graph.get_graph().draw_mermaid_png()
            
            # Save the PNG
            with open(image_path, "wb") as f:
                f.write(png_data)
            
            logger.info(f"✅ Graph PNG saved to {image_path}")
            return str(image_path)
            
        except Exception as png_error:
            logger.error(f"Failed to generate PNG for {graph_name}: {png_error}")
            logger.info("Attempting alternative visualization method...")
            
            try:
                # Alternative: Save as Mermaid text
                mermaid_text = compiled_graph.get_graph().draw_mermaid()
                text_path = image_path.with_suffix('.mmd')
                with open(text_path, 'w') as f:
                    f.write(mermaid_text)
                logger.info(f"✅ Mermaid diagram saved to {text_path}")
                return str(text_path)
            except Exception as mmd_error:
                logger.error(f"Alternative visualization also failed: {mmd_error}")
                return None
    
    except Exception as e:
        logger.error(f"❌ Failed to visualize {graph_name}: {e}")
        return None


def visualize_all_graphs():
    """Visualize and save all graphs."""
    print("🏗️  Building and visualizing all LangGraph workflows...\n")
    
    graphs = {
        "Conversation Manager": ConversationManagerGraph(),
        "Product Retrieval": ProductRetrievalGraph(DEPOSIT_ACCOUNTS_CONFIG),
        "Comparison": ComparisonGraph(),
    }
    
    logger.info(f"📁 Saving graphs to: {IMAGES_DIR}\n")
    
    for name, graph_instance in graphs.items():
        try:
            visualize_graph(graph_instance, name)
        except Exception as e:
            logger.error(f"❌ Error visualizing {name}: {e}")
    
    print(f"\n✅ All graphs processed! Images saved to: {IMAGES_DIR}")


if __name__ == "__main__":
    visualize_all_graphs()


