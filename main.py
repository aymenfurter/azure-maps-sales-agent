import json
import os

import gradio as gr
import plotly.graph_objects as go
from azure.ai.projects import AIProjectClient
from azure.ai.projects.models import BingGroundingTool, FunctionTool, ToolSet
from azure.identity import DefaultAzureCredential
from dotenv import load_dotenv
from opentelemetry import trace

from chat_ui import create_chat_interface
from sales_functions import (
    generate_location_map,
    get_clients_for_today,
    get_current_visit_status,
    get_next_visit,
    plan_optimal_route,
    reset_sales_day,
)

load_dotenv(override=True)

tracer = trace.get_tracer(__name__)

credential = DefaultAzureCredential()
project_client = AIProjectClient.from_connection_string(
    credential=credential, conn_str=os.environ["PROJECT_CONNECTION_STRING"]
)

bing_tool = None
bing_connection_name = os.environ.get("BING_CONNECTION_NAME")
if bing_connection_name:
    try:
        with tracer.start_as_current_span("setup_bing_tool") as span:
            span.set_attribute("bing_connection_name", bing_connection_name)
            bing_connection = project_client.connections.get(connection_name=bing_connection_name)
            conn_id = bing_connection.id
            bing_tool = BingGroundingTool(connection_id=conn_id)
            print("bing > connected")
    except Exception as ex:
        print(f"bing > not connected: {ex}")

AGENT_NAME = "sales-planning-agent"

with tracer.start_as_current_span("setup_agent") as span:
    span.set_attribute("agent_name", AGENT_NAME)
    span.set_attribute("model", os.environ.get("MODEL_DEPLOYMENT_NAME", "gpt-4o"))

    found_agent = next((a for a in project_client.agents.list_agents().data if a.name == AGENT_NAME), None)

    toolset = ToolSet()

    if bing_tool:
        toolset.add(bing_tool)

    toolset.add(
        FunctionTool(
            {
                get_clients_for_today,
                plan_optimal_route,
                get_next_visit,
                get_current_visit_status,
                generate_location_map,
                reset_sales_day,
            }
        )
    )

    instructions = """
    You are a helpful Sales Planning Assistant designed to help sales professionals plan and execute their daily client visits.
    Follow these rules:

    1. **Get Clients:** When the user asks about today's clients or schedule, use `get_clients_for_today` to retrieve
       the list of clients to visit.

    2. **Plan Route:** When the user asks to plan or optimize their route, use `plan_optimal_route` to get the most efficient
       route between client locations. Always explain the route plan clearly with distance, time, and visit order.

    3. **Next Visit:** When the user asks about their next client or what's next on their schedule, use `get_next_visit`
       to advance to the next client in the optimized route.

    4. **Current Status:** If the user asks about their current location or progress, use `get_current_visit_status`
       to check which client they're currently visiting.

    5. **Show Maps:** When the user asks to see a location or needs directions, use `generate_location_map` to create
       a static map image for their current or next location. Explain the map is being generated, then display it when ready.

    6. **Reset Day:** If the user wants to start over or plan a different route, use `reset_sales_day`
       to clear the current plan.

    7. **Be Conversational:** Maintain a helpful, conversational tone. Remember that you're assisting someone who is
       potentially driving between client locations.

    8. **Provide Context:** Always provide useful context with each response, such as travel time to the next location,
       important client notes, or details about the current visit.

    9. **General Questions:** For questions not related to sales planning, use the Bing grounding tool when appropriate.

    10. **Display Images:** When showing a map, make sure to display the image and explain
       what the user is seeing.

    Always ask if the user needs any more information about their sales route or client visits.
    """

    agent_model = os.environ.get("MODEL_DEPLOYMENT_NAME", "gpt-4o")

    if found_agent:
        span.set_attribute("agent_action", "update")
        agent = project_client.agents.update_agent(
            assistant_id=found_agent.id, model=agent_model, name=AGENT_NAME, instructions=instructions, toolset=toolset
        )
    else:
        span.set_attribute("agent_action", "create")
        agent = project_client.agents.create_agent(
            model=agent_model, name=AGENT_NAME, instructions=instructions, toolset=toolset
        )
    print(f"Agent '{agent.name}' (ID: {agent.id}) is ready using model '{agent.model}'.")

with tracer.start_as_current_span("create_thread") as span:
    thread = project_client.agents.create_thread()
    span.set_attribute("thread_id", thread.id)
    print(f"Created new thread: {thread.id}")

azure_sales_chat = create_chat_interface(project_client, agent, thread, tracer)


def process_route_data(route_file="/workspaces/appmag/route_response.json"):
    try:
        with open(route_file, "r") as f:
            data = json.load(f)

        if not data.get("routes"):
            return None, []

        route = data["routes"][0]
        coordinates = []
        instructions = []

        for instruction in route["guidance"]["instructions"]:
            if "point" in instruction:
                instructions.append(
                    {
                        "type": instruction["instructionType"],
                        "street": instruction.get("street", ""),
                        "message": instruction.get("message", ""),
                        "lat": instruction["point"]["latitude"],
                        "lon": instruction["point"]["longitude"],
                    }
                )
                coordinates.append([instruction["point"]["latitude"], instruction["point"]["longitude"]])

        fig = go.Figure()

        # Add route line
        lat_list = [point[0] for point in coordinates]
        lon_list = [point[1] for point in coordinates]

        fig.add_trace(
            go.Scattermapbox(
                lat=lat_list, lon=lon_list, mode="lines", line=dict(width=2, color="blue"), name="Route", showlegend=False
            )
        )

        marker_props = {
            "LOCATION_DEPARTURE": {"color": "green", "size": 15},
            "LOCATION_WAYPOINT": {"color": "blue", "size": 15},
            "LOCATION_ARRIVAL": {"color": "red", "size": 15},
            "TURN": {"color": "orange", "size": 8},
        }

        for instr in instructions:
            props = marker_props.get(instr["type"], {"color": "gray", "size": 6})

            hover_text = f"Type: {instr['type']}<br>" f"Street: {instr['street']}<br>" f"Action: {instr['message']}"

            fig.add_trace(
                go.Scattermapbox(
                    lat=[instr["lat"]],
                    lon=[instr["lon"]],
                    mode="markers",
                    marker=dict(size=props["size"], color=props["color"]),
                    text=[hover_text],
                    name=instr["type"],
                    showlegend=False,
                    hoverinfo="text",
                )
            )

        # Center map on Switzerland
        fig.update_layout(
            mapbox=dict(style="open-street-map", center=dict(lat=46.8, lon=8.2), zoom=7),
            margin=dict(l=0, r=0, t=0, b=0),
            height=600,
            showlegend=False,  # Add this line to disable legend completely
        )

        # Extract navigation sections
        nav_sections = []
        for group in route["guidance"]["instructionGroups"]:
            nav_sections.append([f"Section {len(nav_sections) + 1}", group["groupMessage"]])

        return fig, nav_sections
    except Exception as e:
        print(f"Error processing route data: {e}")
        return None, []


with gr.Blocks(
    title="Sales Planning Assistant",
    fill_height=True,
    css="""
            .chat-area { height:65vh !important; overflow:auto; }
            .input-area { position:sticky; bottom:0; }
            .route-section { border-top: 2px solid #eee; padding-top: 20px; margin-top: 20px; }
        """,
) as demo:
    gr.Markdown("## Sales Planning Assistant")
    gr.Markdown("*Plan your sales day and navigate client visits with AI assistance*")

    with gr.Row():
        with gr.Column(scale=2):
            chatbot = gr.Chatbot(type="messages", label="Chat History", elem_classes="chat-area", layout="panel")
            input_box = gr.Textbox(label="Ask the assistant …", elem_classes="input-area")
        with gr.Column(scale=1, elem_classes="route-section"):
            gr.Markdown("### Route Visualization")
            view_route_btn = gr.Button("Visualize Last Route")
            route_map = gr.Plot(label="Route Map")
            route_accordion = gr.Accordion("Navigation Instructions", open=False)
            with route_accordion:
                navigation = gr.Dataframe(
                    headers=["Section", "Instructions"], datatype=["str", "str"], label="Route Instructions"
                )

    def clear_history():
        with tracer.start_as_current_span("clear_chat_history") as span:
            global thread, azure_sales_chat
            print(f"Clearing history. Old thread: {thread.id}")
            thread = project_client.agents.create_thread()
            azure_sales_chat = create_chat_interface(project_client, agent, thread, tracer)
            span.set_attribute("new_thread_id", thread.id)
            print(f"New thread: {thread.id}")
            return []

    with gr.Row():
        clear_button = gr.Button("Clear Chat History")

    gr.Markdown("### Example Questions")
    with gr.Row():
        q1 = gr.Button("Who are my clients today?")
        q2 = gr.Button("Plan my optimal rout (including detailed directions for each leg)?")
        q4 = gr.Button("Show me a map of my next location")
    clear_button.click(fn=clear_history, outputs=chatbot).then(lambda: "", outputs=input_box)

    def set_example_question(question):
        with tracer.start_as_current_span("select_example_question") as span:
            span.set_attribute("example_question", question)
            return question

    example_buttons = [q1, q2, q4]
    for btn in example_buttons:
        btn.click(lambda x=btn.value: set_example_question(x), inputs=[], outputs=input_box).then(
            lambda: [], outputs=chatbot
        ).then(azure_sales_chat, inputs=[input_box, chatbot], outputs=[chatbot, input_box], show_progress="full").then(
            lambda: "", outputs=input_box
        )

    input_box.submit(azure_sales_chat, inputs=[input_box, chatbot], outputs=[chatbot, input_box], show_progress="full").then(
        lambda: "", outputs=input_box
    )

    def visualize_route():
        fig, nav_sections = process_route_data()
        if fig:
            return fig, nav_sections
        return None, []

    view_route_btn.click(visualize_route, outputs=[route_map, navigation])

if __name__ == "__main__":
    if not os.environ.get("AZURE_MAPS_KEY"):
        print("\n⚠️ WARNING: AZURE_MAPS_KEY environment variable not found!")
        print("This application requires an Azure Maps API key to function properly.")
        print("You can set it by running:")
        print("export AZURE_MAPS_KEY=your_key_here\n")

    server_name = os.environ.get("GRADIO_SERVER_NAME", "0.0.0.0")
    server_port = int(os.environ.get("GRADIO_SERVER_PORT", 7860))

    demo.queue().launch(server_name=server_name, server_port=server_port, share=False, debug=True, show_error=True)
