from google.adk.tools import FunctionTool
import yaml
from utils.util_functions import get_logger
from utils.constants import FLOW_CONFIG

logger = get_logger(__name__)



# Load your conversation configuration
with open(FLOW_CONFIG, "r") as f:
    CONVERSATION_TREE = yaml.safe_load(f)["conversation_tree"]
    logger.debug("config tree loaded")
CONVERSATION_NODES = {node["id"]: node for node in CONVERSATION_TREE}

class ConversationTools:
    def __init__(self, session_service):
        self.session_service = session_service # To access/update session state

    def lookup_products(self, product_type: str) -> str:
        """Looks up available products based on type."""
        # Placeholder for actual product database lookup
        if "electronics" in product_type.lower():
            return "We have a wide range of laptops, smartphones, and headphones."
        elif "clothing" in product_type.lower():
            return "Our clothing collection includes shirts, pants, and dresses."
        else:
            return "I couldn't find products for that type."

    def get_order_status(self, order_number: str) -> str:
        """Retrieves the status of an order."""
        # Placeholder for actual order system lookup
        if order_number == "123456789":
            return "Your order #123456789 is currently out for delivery and expected by tomorrow."
        else:
            return "Sorry, I couldn't find an order with that number."

    def get_current_weather(self, location: str) -> str:
        """Fetches current weather for a specified location."""
        # In Keysborough, Victoria, Australia
        # You'd use a real weather API here
        if location.lower() == "melbourne":
            return "The weather in Melbourne is currently partly cloudy with 20 degrees Celsius."
        elif location.lower() == "sydney":
            return "The weather in Sydney is sunny with 25 degrees Celsius."
        else:
            return f"Sorry, I don't have real-time weather data for {location}."

    def transition_dialogue(self, next_node_id: str, entities: dict = None) -> str:
        """
        Internal tool to transition the conversation to a new node.
        This tool doesn't generate a user-facing response directly,
        but updates the session state and signals the orchestrator.
        """
        session_id = self.session_service.current_session.session_id
        session_data = self.session_service.get_session_data(session_id)
        session_data["current_node_id"] = next_node_id
        if entities:
            session_data.update(entities) # Store extracted entities
        self.session_service.update_session_data(session_id, session_data)
        return f"Transitioned to node: {next_node_id}" # This is for internal logging/debugging