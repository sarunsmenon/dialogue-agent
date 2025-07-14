from google.adk.agents import Agent
from google.adk.tools import FunctionTool
from google.adk.io import Content
from tools import ConversationTools, CONVERSATION_NODES
import json

class DynamicDialogueAgent(Agent):
    def __init__(self, session_service):
        super().__init__(
            name="dynamic_dialogue_agent",
            description="An agent that manages a dynamic conversation flow based on a configurable tree.",
            model="gemini-pro", # Or your preferred LLM
            tools=[
                FunctionTool(ConversationTools(session_service).lookup_products),
                FunctionTool(ConversationTools(session_service).get_order_status),
                FunctionTool(ConversationTools(session_service).get_current_weather),
                FunctionTool(ConversationTools(session_service).transition_dialogue),
            ],
            instruction=self._get_initial_instruction()
        )
        self.session_service = session_service

    def _get_initial_instruction(self):
        # This prompt guides the LLM to understand its role in flow control
        return """
        You are a conversational AI designed to guide users through a series of questions.
        Your task is to understand the user's intent based on their response to the current question,
        and then determine the appropriate next step in the conversation flow by calling the
        `transition_dialogue` tool with the `next_node_id`.

        Here's how you should operate:
        1.  **Receive Current Question and User Input:** You will be provided with the current question asked and the user's latest response.
        2.  **Identify Intent:** Based on the user's response, identify their intent.
        3.  **Determine Next Node:** Consult the provided `expected_responses` for the current question to find the best matching `next_node_id`.
            * If a strong match is found, call the `transition_dialogue` tool with that `next_node_id`.
            * If no specific match, use the `default_next_node_id`.
        4.  **Extract Entities:** If necessary, extract relevant entities (like product_type, order_number, location) from the user's input and pass them as `entities` argument to the `transition_dialogue` tool.
        5.  **Tool Execution:** If the determined next node has an `action` defined, anticipate that action will be performed after the transition.
        6.  **Response Generation (Crucial):** After transitioning (or if no tool is explicitly called from the LLM's side, e.g. for simple transitions), your final response should be the *question* of the `next_node_id`, formatted naturally. If the next node is an `end_of_path`, provide a concluding statement.

        **Crucial:** Do NOT generate the next question yourself without explicitly getting the `next_node_id` from the configuration via the `transition_dialogue` tool. The `transition_dialogue` tool is how you signal to the system which path to take.

        Your output should be a tool call to `transition_dialogue` or, if a final response is to be given, the text of that response.
        """

    def _get_prompt_for_llm(self, current_node_id, user_message_text):
        # This method constructs the specific prompt for the LLM based on the current state.
        current_node = CONVERSATION_NODES.get(current_node_id)
        if not current_node:
            return "Error: Invalid conversation node."

        question = current_node["question"]
        expected_responses_info = ""
        if "expected_responses" in current_node:
            expected_responses_info = "\nConsider these possible user intents and their corresponding next steps:"
            for res in current_node["expected_responses"]:
                keywords = ", ".join(res.get("keywords", []))
                patterns = ", ".join(res.get("patterns", []))
                expected_responses_info += f"\n- If user mentions keywords '{keywords}' or matches patterns '{patterns}', go to node '{res['next_node_id']}'."

        default_next = current_node.get("default_next_node_id", "start")

        prompt = f"""
        Current Question: "{question}"
        User's Response: "{user_message_text}"

        Based on the user's response, determine the most appropriate `next_node_id`.
        {expected_responses_info}
        If none of the above matches strongly, use the `default_next_node_id` which is '{default_next}'.

        After determining the `next_node_id`, you MUST call the `transition_dialogue` tool with this `next_node_id` and any extracted `entities`.
        For example: `transition_dialogue(next_node_id="ask_product_type", entities={{"product_type": "electronics"}})`

        If the `next_node_id` implies a tool should be run (e.g. `lookup_products` for "electronics" in `ask_product_type`), extract the necessary arguments for that tool and include them in the `entities` parameter of `transition_dialogue`.
        """
        return prompt


    async def _run(self, session_id: str, user_message: Content):
        # This is where the core logic for each turn happens.
        session_data = self.session_service.get_session_data(session_id)
        current_node_id = session_data.get("current_node_id", "start") # Get current node, default to start

        current_node = CONVERSATION_NODES.get(current_node_id)

        if current_node.get("end_of_path"):
            yield Content(text=current_node["question"].format(**session_data)) # Format final message with stored data
            return # End conversation for this path

        # Construct the prompt for the LLM to decide the next step
        llm_prompt = self._get_prompt_for_llm(current_node_id, user_message.text)

        # Let the LLM decide the next step (tool call to transition_dialogue)
        llm_output = await self.model.call_async(llm_prompt, tools=self.tools)

        # The LLM should have made a tool call to transition_dialogue
        # We need to explicitly check and execute it if it's the right tool
        if llm_output.tool_code and llm_output.tool_name == "transition_dialogue":
            tool_args = json.loads(llm_output.tool_args_json)
            next_node_id = tool_args.get("next_node_id")
            entities = tool_args.get("entities", {})

            # Call the internal transition tool
            await self.transition_dialogue(next_node_id=next_node_id, entities=entities)

            # Now, retrieve the new current_node_id from the updated session data
            updated_session_data = self.session_service.get_session_data(session_id)
            new_current_node_id = updated_session_data.get("current_node_id")
            new_current_node = CONVERSATION_NODES.get(new_current_node_id)

            if new_current_node:
                # If the new node has an action, run it and provide its output to the user
                if "action" in new_current_node:
                    action_tool_name = new_current_node["action"]
                    tool_func = getattr(self._tools_instance, action_tool_name, None)
                    if tool_func:
                        # Pass relevant entities as arguments to the tool
                        # This part needs careful handling of arguments based on tool signature
                        tool_result = ""
                        if action_tool_name == "lookup_products":
                            product_type = entities.get("product_type", "")
                            tool_result = tool_func(product_type=product_type)
                        elif action_tool_name == "get_order_status":
                            order_number = entities.get("order_number", "")
                            tool_result = tool_func(order_number=order_number)
                        elif action_tool_name == "get_current_weather":
                            location = entities.get("location", "")
                            tool_result = tool_func(location=location)

                        # Incorporate tool result into the LLM's response
                        response_text = new_current_node["question"]
                        # A simple way to inject tool_result into the question, you might need more sophisticated templating
                        response_text = response_text.replace("{location}", entities.get("location", ""))
                        response_text = response_text.replace("{weather_data}", tool_result)
                        response_text = response_text.replace("{order_data}", tool_result) # Example for order status
                        yield Content(text=response_text)
                    else:
                        yield Content(text=f"Error: Tool '{action_tool_name}' not found.")
                else:
                    # If no specific action, just ask the question from the new node
                    yield Content(text=new_current_node["question"])
            else:
                yield Content(text="I'm sorry, I seem to have lost my way. Can we start over?")
        else:
            # Fallback if LLM doesn't call transition_dialogue as expected
            yield Content(text="I'm not sure how to proceed. Could you please rephrase?")