from chat_ui import create_chat_interface
import gradio as gr
from sales_functions import (
    get_clients_for_today,
    plan_optimal_route,
    get_next_visit,
    get_current_visit_status,
    generate_location_map,
    reset_sales_day
)
from azure.ai.projects.models import (
    BingGroundingTool,
    FunctionTool,
    ToolSet
)
from azure.ai.projects import AIProjectClient
from azure.identity import DefaultAzureCredential
import os
from opentelemetry import trace
from dotenv import load_dotenv

load_dotenv(override=True)

tracer = trace.get_tracer(__name__)

credential = DefaultAzureCredential()
project_client = AIProjectClient.from_connection_string(
    credential=credential,
    conn_str=os.environ["PROJECT_CONNECTION_STRING"]
)

bing_tool = None
bing_connection_name = os.environ.get("BING_CONNECTION_NAME")
if bing_connection_name:
    try:
        with tracer.start_as_current_span("setup_bing_tool") as span:
            span.set_attribute("bing_connection_name", bing_connection_name)
            bing_connection = project_client.connections.get(
                connection_name=bing_connection_name)
            conn_id = bing_connection.id
            bing_tool = BingGroundingTool(connection_id=conn_id)
            print("bing > connected")
    except Exception as ex:
        print(f"bing > not connected: {ex}")

AGENT_NAME = "sales-planning-agent"

with tracer.start_as_current_span("setup_agent") as span:
    span.set_attribute("agent_name", AGENT_NAME)
    span.set_attribute("model", os.environ.get(
        "MODEL_DEPLOYMENT_NAME", "gpt-4o"))

    found_agent = next(
        (a for a in project_client.agents.list_agents().data if a.name == AGENT_NAME),
        None
    )

    toolset = ToolSet()

    if bing_tool:
        toolset.add(bing_tool)

    toolset.add(FunctionTool({
        get_clients_for_today,
        plan_optimal_route,
        get_next_visit,
        get_current_visit_status,
        generate_location_map,
        reset_sales_day
    }))

    instructions = """
    You are a helpful Sales Planning Assistant designed to help sales professionals plan and execute their daily client visits. Follow these rules:

    1. **Get Clients:** When the user asks about today's clients or schedule, use `get_clients_for_today` to retrieve the list of clients to visit.

    2. **Plan Route:** When the user asks to plan or optimize their route, use `plan_optimal_route` to get the most efficient route between client locations. Always explain the route plan clearly with total distance, time, and the order of visits.

    3. **Next Visit:** When the user asks about their next client or what's next on their schedule, use `get_next_visit` to advance to the next client in the optimized route.

    4. **Current Status:** If the user asks about their current location or progress, use `get_current_visit_status` to check which client they're currently visiting.

    5. **Show Maps:** When the user asks to see a location or needs directions, use `generate_location_map` to create a static map image for their current or next location. Explain the map is being generated, then display it when ready.

    6. **Reset Day:** If the user wants to start over or plan a different route, use `reset_sales_day` to clear the current plan.

    7. **Be Conversational:** Maintain a helpful, conversational tone. Remember that you're assisting someone who is potentially driving between client locations.

    8. **Provide Context:** Always provide useful context with each response, such as travel time to the next location, important client notes, or details about the current visit.

    9. **General Questions:** For questions not related to sales planning, use the Bing grounding tool when appropriate.

    10. **Display Images:** When showing a map, make sure to display the image and explain what the user is seeing.

    Always ask if the user needs any more information about their sales route or client visits.
    """

    agent_model = os.environ.get(
        "MODEL_DEPLOYMENT_NAME", "gpt-4o")

    if found_agent:
        span.set_attribute("agent_action", "update")
        agent = project_client.agents.update_agent(
            assistant_id=found_agent.id,
            model=agent_model,
            name=AGENT_NAME,
            instructions=instructions,
            toolset=toolset
        )
    else:
        span.set_attribute("agent_action", "create")
        agent = project_client.agents.create_agent(
            model=agent_model,
            name=AGENT_NAME,
            instructions=instructions,
            toolset=toolset
        )
    print(
        f"Agent '{agent.name}' (ID: {agent.id}) is ready using model '{agent.model}'.")

with tracer.start_as_current_span("create_thread") as span:
    thread = project_client.agents.create_thread()
    span.set_attribute("thread_id", thread.id)
    print(f"Created new thread: {thread.id}")

azure_sales_chat = create_chat_interface(project_client, agent, thread, tracer)

with gr.Blocks(
        title="Sales Planning Assistant",
        fill_height=True,
        css="""
            .chat-area   {height:65vh !important; overflow:auto;}
            .input-area  {position:sticky; bottom:0;}
        """
) as demo:
    gr.Markdown("## Sales Planning Assistant")
    gr.Markdown(
        "*Plan your sales day and navigate client visits with AI assistance*")

    chatbot = gr.Chatbot(
        type="messages",
        label="Chat History",
        elem_classes="chat-area",
        layout="panel"
    )
    input_box = gr.Textbox(
        label="Ask the assistant …",
        elem_classes="input-area"
    )

    def clear_history():
        with tracer.start_as_current_span("clear_chat_history") as span:
            global thread, azure_sales_chat
            print(f"Clearing history. Old thread: {thread.id}")
            thread = project_client.agents.create_thread()
            azure_sales_chat = create_chat_interface(
                project_client, agent, thread, tracer)
            span.set_attribute("new_thread_id", thread.id)
            print(f"New thread: {thread.id}")
            return []

    with gr.Row():
        clear_button = gr.Button("Clear Chat History")

    gr.Markdown("### Example Questions")
    with gr.Row():
        q1 = gr.Button("Who are my clients today?")
        q2 = gr.Button(
            "Plan my optimal rout (including detailed directions for each leg)?")
        q4 = gr.Button("Show me a map of my next location")
    clear_button.click(
        fn=clear_history,
        outputs=chatbot
    ).then(
        lambda: "",
        outputs=input_box
    )

    def set_example_question(question):
        with tracer.start_as_current_span("select_example_question") as span:
            span.set_attribute("example_question", question)
            return question

    example_buttons = [q1, q2, q4]
    for btn in example_buttons:
        btn.click(lambda x=btn.value: set_example_question(
            x), inputs=[], outputs=input_box
        ).then(lambda: [], outputs=chatbot
               ).then(azure_sales_chat, inputs=[input_box, chatbot], outputs=[chatbot, input_box], show_progress="full"
                      ).then(lambda: "", outputs=input_box)

    input_box.submit(azure_sales_chat, inputs=[input_box, chatbot], outputs=[
                     chatbot, input_box], show_progress="full"
                     ).then(lambda: "", outputs=input_box)

if __name__ == "__main__":
    if not os.environ.get("AZURE_MAPS_KEY"):
        print("\n⚠️ WARNING: AZURE_MAPS_KEY environment variable not found!")
        print("This application requires an Azure Maps API key to function properly.")
        print("You can set it by running:")
        print("export AZURE_MAPS_KEY=your_key_here\n")

    server_name = os.environ.get("GRADIO_SERVER_NAME", "0.0.0.0")
    server_port = int(os.environ.get("GRADIO_SERVER_PORT", 7860))

    demo.queue().launch(
        server_name=server_name,
        server_port=server_port,
        share=False,
        debug=True,
        show_error=True
    )
