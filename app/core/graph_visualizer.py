from pathlib import Path
from typing import Union, Any
from langgraph.graph import StateGraph

IMAGES_DIR = Path(__file__).parent / "images"
IMAGES_DIR.mkdir(exist_ok=True)


def save_graph_visualization(graph: Union[StateGraph, Any], name: str) -> str:
    try:
        # If it's a StateGraph, compile it first
        if isinstance(graph, StateGraph):
            compiled_graph = graph.compile()
        else:
            compiled_graph = graph
        
        # Try to get the graph and draw it
        try:
            graph_obj = compiled_graph.get_graph()
            image_data = graph_obj.draw_mermaid_png()
        except (AttributeError, Exception):
            # Fallback: just skip if visualization is not available
            return None
            
        output_path = IMAGES_DIR / f"{name}.png"
        with open(output_path, "wb") as f:
            f.write(image_data)
        return str(output_path)
    except Exception as e:
        print(f"Error saving graph visualization for {name}: {e}")
        return None


def save_all_graphs(graphs_dict: dict) -> None:
    for name, graph in graphs_dict.items():
        save_graph_visualization(graph, name)
