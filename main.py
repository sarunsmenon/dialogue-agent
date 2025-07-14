import logging
from dotenv import load_dotenv
from utils.util_functions import setup_defaults, get_logger
import asyncio
from google.adk.services import InMemorySessionService
from google.adk.runners import Runner
from google.adk.io import Content
from models.agent import DynamicDialogueAgent
from models.tools import ConversationTools # Import to initialize tools for the agent

load_dotenv()
setup_defaults()

logger = get_logger()



async def main():
    session_service = InMemorySessionService()
    # Initialize ConversationTools instance and pass it to the agent
    # The agent's __init__ will then access the actual tool functions
    logger.debug("session service initiated as :: %s", session_service)
    conversation_tools_instance = ConversationTools(session_service)
    agent = DynamicDialogueAgent(session_service)
    logger.debug("agent created as %s", agent)
    agent._tools_instance = conversation_tools_instance # Hacky way to give agent access to tool instance for direct calls

    runner = Runner(
        root_agent=agent,
        session_service=session_service
    )

    session_id = "user_123"

    print("Agent: Hello! What can I help you with today? (e.g., find a product, check order status, or something else?)")

    while True:
        user_input = input("You: ")
        if user_input.lower() == "exit":
            break

        user_message = Content(text=user_input)

        # Manually set the initial node for a new session
        # For subsequent turns, the LLM will manage the transition via transition_dialogue
        session_data = session_service.get_session_data(session_id)
        if "current_node_id" not in session_data:
            session_service.update_session_data(session_id, {"current_node_id": "start"})

        async for event in runner.run_async(session_id=session_id, user_message=user_message):
            if event.is_final_response():
                print(f"Agent: {event.text}")
            # You can add more debugging here to see tool calls, LLM thoughts etc.
            # elif event.is_tool_code():
            #     print(f"Tool Code: {event.text}")
            # elif event.is_llm_thought():
            #     print(f"LLM Thought: {event.thought}")

if __name__ == "__main__":
    asyncio.run(main())
