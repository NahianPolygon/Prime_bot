from langgraph.graph import StateGraph, END
from typing import Any
from app.models.conversation_state import ConversationState
from app.core.graph_visualizer import save_graph_visualization


class RAGExplanationGraph:
    def __init__(self, openai_client=None, embedding_model=None):
        self._graph = None
        self.client = openai_client
        self.embedding_model = embedding_model

    def retrieve_documents_node(self, state: ConversationState) -> dict:
        query = state.response or "banking products information"
        retrieved_docs = [
            {
                "title": "Deposit Products Guide",
                "content": "Deposit products include savings accounts, fixed deposits, and monthly savings schemes."
            },
            {
                "title": "Credit Products Guide",
                "content": "Credit products include credit cards, personal loans, and overdrafts."
            }
        ]
        
        return {
            "response": f"Retrieved {len(retrieved_docs)} relevant documents."
        }

    def grounded_generation_node(self, state: ConversationState) -> dict:
        context = "Based on banking product documentation: "
        
        if state.banking_type == "deposit":
            context += "Deposit products help you save money safely with interest benefits."
        elif state.banking_type == "credit":
            context += "Credit products provide borrowing solutions with flexible repayment."
        
        if state.eligible_products:
            context += f" Recommended products: {', '.join(state.eligible_products[:2])}"
        
        return {
            "response": context
        }

    def format_explanation_node(self, state: ConversationState) -> dict:
        explanation = f"Here's what you need to know:\n\n{state.response}\n\n"
        explanation += "This recommendation is based on your profile and banking needs."
        
        return {
            "response": explanation
        }

    def build_graph(self) -> Any:
        graph = StateGraph(ConversationState)
        
        graph.add_node("retrieve_documents", self.retrieve_documents_node)
        graph.add_node("grounded_generation", self.grounded_generation_node)
        graph.add_node("format_explanation", self.format_explanation_node)
        
        graph.set_entry_point("retrieve_documents")
        graph.add_edge("retrieve_documents", "grounded_generation")
        graph.add_edge("grounded_generation", "format_explanation")
        graph.add_edge("format_explanation", END)
        
        self._graph = graph.compile()
        save_graph_visualization(graph, "graph_5_rag_explanation")
        return self._graph
    
    def invoke(self, state: ConversationState) -> ConversationState:
        graph = self.build_graph()
        if isinstance(state, dict):
            state_obj = ConversationState(**state)
            state_dict = state
        else:
            state_obj = state
            state_dict = state.model_dump()
        
        result = graph.invoke(state_dict)
        
        updated_fields = {
            "response": result.get("response", state_obj.response)
        }
        
        return ConversationState(**{**state_obj.model_dump(), **updated_fields})
