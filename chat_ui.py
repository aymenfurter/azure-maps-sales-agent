import json
import time
from typing import List, Optional

from azure.ai.projects.models import (
    AgentEventHandler,
    MessageDeltaChunk,
    RunStep,
    RunStepDeltaChunk,
    ThreadMessage,
    ThreadRun,
)
from gradio import ChatMessage
from opentelemetry import trace


class nullcontext:
    def __init__(self, enter_result=None):
        self.enter_result = enter_result

    def __enter__(self):
        return self.enter_result

    def __exit__(self, *excinfo):
        pass


class EventHandler(AgentEventHandler):
    def __init__(self, tracer=None):
        super().__init__()
        self._current_message_id = None
        self._accumulated_text = ""
        self._current_tools = {}
        self.conversation: Optional[List[ChatMessage]] = None
        self.create_tool_bubble_fn = None
        self.tracer = tracer
        self.current_tool_calls = {}
        self._message_map = {}

    def on_message_delta(self, delta: MessageDeltaChunk) -> None:
        if delta.id != self._current_message_id:
            self._current_message_id = delta.id
            self._accumulated_text = ""
            print("\nassistant> ", end="")

            if self.conversation is not None:
                new_msg = ChatMessage(role="assistant", content="")
                self.conversation.append(new_msg)
                self._message_map[delta.id] = new_msg

        partial_text = ""
        for chunk in delta.delta.content or []:
            if hasattr(chunk, "text") and chunk.text:
                partial_text += chunk.text.get("value", "")

        if partial_text:
            self._accumulated_text += partial_text
            print(partial_text, end="", flush=True)

            if self.conversation:
                target_msg = self._message_map.get(delta.id)
                if target_msg:
                    target_msg.content = self._accumulated_text

    def on_thread_message(self, message: ThreadMessage) -> None:
        print(f"\nDEBUG: on_thread_message - ID: {message.id}, Role: {message.role}, Status: {message.status}")
        if message.role == "assistant" and message.status == "completed":
            final_content = ""
            if message.content:
                for content_part in message.content:
                    if hasattr(content_part, "text") and content_part.text:
                        final_content += content_part.text.value

            print(f"\nAssistant message completed (ID: {message.id}): {final_content[:500]}...")

            if self.conversation:
                mapped = self._message_map.get(message.id)
                if mapped:
                    mapped.content = final_content
                elif final_content:
                    self.conversation.append(ChatMessage(role="assistant", content=final_content))

    def on_thread_run(self, run: ThreadRun) -> None:
        print(f"\nthread_run status > {run.status} (ID: {run.id})")

        if run.status == "failed":
            print(f"❌ ERROR > Run failed with ID: {run.id}")
            if run.last_error:
                error_msg = f"Error type: {run.last_error.code}, Message: {run.last_error.message}"
                print(f"❌ ERROR DETAILS > {error_msg}")
            else:
                print("❌ ERROR DETAILS > No specific error information available")

            if hasattr(run, "required_action") and run.required_action:
                print(f"⚠️ REQUIRED ACTION > {run.required_action}")

        elif run.status == "completed":
            print(f"✓ Run completed successfully (ID: {run.id})")

        if self.tracer:
            try:
                span = trace.get_current_span()
                if span and hasattr(span, "is_recording") and span.is_recording():
                    span.set_attribute("run_id", run.id)
                    span.set_attribute("run_status", run.status)
                    if run.status == "failed" and run.last_error:
                        span.set_attribute("error_code", run.last_error.code)
                        span.set_attribute("error", run.last_error.message)
            except Exception as ex:
                print(f"WARNING: Failed to record tracing for run: {ex}")

    def on_run_step_delta(self, delta: RunStepDeltaChunk) -> None:
        step_delta = delta.delta.step_details
        if step_delta and step_delta.type == "tool_calls":
            for tcall_delta in step_delta.tool_calls or []:
                call_id = tcall_delta.id
                if not call_id:
                    continue

                if tcall_delta.type == "function" and tcall_delta.function:
                    func_delta = tcall_delta.function
                    if call_id not in self.current_tool_calls:
                        print(f"\nDEBUG: Tool call started: {func_delta.name} (ID: {call_id})")
                        self.current_tool_calls[call_id] = {"name": func_delta.name, "arguments": "", "status": "starting"}
                        if self.create_tool_bubble_fn:
                            self.create_tool_bubble_fn(func_delta.name, "...", call_id, "pending")
                    if func_delta.arguments:
                        self.current_tool_calls[call_id]["arguments"] += func_delta.arguments

    def on_run_step(self, step: RunStep) -> None:
        if self.tracer:
            span = trace.get_current_span()
            if span and span.is_recording():
                span.set_attribute(f"step_{step.id}_type", step.type)
                span.set_attribute(f"step_{step.id}_status", step.status)

        if step.type == "tool_calls" and step.step_details and step.step_details.tool_calls:
            for tcall in step.step_details.tool_calls:
                call_id = tcall.id
                tool_info = self.current_tool_calls.get(call_id)
                func_name = tool_info["name"] if tool_info else "unknown_function"
                output = None

                if step.status == "completed":
                    print(f"Tool call completed: {func_name} (ID: {call_id})")
                    if tcall.type == "function" and hasattr(tcall, "function") and tcall.function.output:
                        output_str = tcall.function.output
                        print(f"  Output: {output_str[:200]}{'...' if len(output_str) > 200 else ''}")
                        try:
                            output = json.loads(output_str)
                            if func_name == "get_shelf_layout" and "layout_visual" in output:
                                message = output["layout_visual"]
                            elif "message" in output:
                                message = output["message"]
                            elif "error" in output:
                                message = f"Error: {output['error']}"
                            elif func_name == "check_item_stock" and "stock" in output:
                                message = f"{output['name']} (ID: {output['item_id']}): {output['stock']} units in stock."
                            elif func_name == "find_item_location" and "location_id" in output:
                                message = f"{output['name']} (ID: {output['item_id']}) is located at Shelf {output['location_id']}, Position {output['position']}."
                            elif func_name == "get_items_needing_restock" and "count" in output:
                                count = output["count"]
                                if count > 0:
                                    items_str = ", ".join(
                                        [f"{i['name']} ({i['current_stock']})" for i in output["low_stock_items"][:3]]
                                    )
                                    message = (
                                        f"Found {count} low stock items. Examples: {items_str}{'...' if count > 3 else ''}."
                                    )
                                else:
                                    message = "No items found needing restock."
                            else:
                                message = f"Completed. Output: {output_str[:1000]}{'...' if len(output_str) > 100 else ''}"

                        except json.JSONDecodeError:
                            message = (
                                f"Completed. Output (non-JSON): {output_str[:1000]}{'...' if len(output_str) > 100 else ''}"
                            )
                            print(f"Warning: Could not parse JSON output for {func_name}: {output_str}")

                    elif tcall.type == "bing_grounding":
                        message = "Finished searching web sources."
                    else:
                        message = "Tool call finished."

                    if self.create_tool_bubble_fn:
                        self.create_tool_bubble_fn(func_name, message, call_id, "done")

                elif step.status == "failed":
                    error_message = f"Tool call failed: {func_name} (ID: {call_id})"
                    if step.last_error:
                        error_message += f" - Error: {step.last_error.message}"
                    print(error_message)
                    if self.tracer and span and span.is_recording():
                        span.set_attribute(f"step_{step.id}_error", error_message)
                    if self.create_tool_bubble_fn:
                        self.create_tool_bubble_fn(func_name, error_message, call_id, "error")

                if call_id in self.current_tool_calls:
                    del self.current_tool_calls[call_id]


def convert_dict_to_chatmessage(msg: dict) -> ChatMessage:
    return ChatMessage(role=msg["role"], content=msg["content"], metadata=msg.get("metadata"))


def convert_chatmessage_to_dict(msg: ChatMessage) -> dict:
    return {"role": msg.role, "content": msg.content, "metadata": msg.metadata if msg.metadata else {}}


def create_chat_interface(project_client, agent, thread, tracer=None):
    last_message_sent_time = 0
    conversation_state: List[ChatMessage] = []

    def create_span(name, parent_span=None):
        if not tracer:
            return nullcontext()

        try:
            if parent_span:
                return tracer.start_as_current_span(name, parent=parent_span)
            else:
                return tracer.start_as_current_span(name)
        except TypeError:
            print("DEBUG: Tracer doesn't support parent parameter, using simpler span creation")
            return tracer.start_as_current_span(name)
        except Exception as e:
            print(f"WARNING: Could not create span: {e}")
            return nullcontext()

    def azure_store_chat(user_message: str, history: List[dict]):
        nonlocal last_message_sent_time
        nonlocal conversation_state
        current_time = time.time()

        if current_time - last_message_sent_time < 2:
            print("WARN: Duplicate message submission detected, skipping.")
            yield history, ""
            return

        if not user_message.strip():
            print("WARN: Empty message received, skipping.")
            yield history, ""
            return

        last_message_sent_time = current_time

        if history:
            conversation_state = [convert_dict_to_chatmessage(m) for m in history]
        conversation: List[ChatMessage] = conversation_state

        print(f"\nUser message: {user_message}")
        conversation.append(ChatMessage(role="user", content=user_message))
        yield [convert_chatmessage_to_dict(m) for m in conversation], ""

        chat_span = None
        if tracer:
            chat_span = tracer.start_span("store_chat_interaction")
            if chat_span and hasattr(chat_span, "is_recording") and chat_span.is_recording():
                chat_span.set_attribute("user_message", user_message)
                chat_span.set_attribute("thread_id", thread.id)
                chat_span.set_attribute("agent_id", agent.id)
                chat_span.set_attribute("conversation_length_start", len(conversation))

        try:
            try:
                project_client.agents.create_message(thread_id=thread.id, role="user", content=user_message)
                print(f"Message sent to thread {thread.id}")
            except Exception as msg_ex:
                print(f"❌ ERROR sending message: {msg_ex}")
                error_msg = ChatMessage(role="assistant", content=f"Error sending message: {str(msg_ex)}")
                conversation.append(error_msg)
                yield [convert_chatmessage_to_dict(m) for m in conversation], ""
                return

            tool_titles = {
                "bing_grounding": "🔎 Searching Web Sources",
                "generate_location_map": "🗺️ Generating Map",
                "get_clients_for_today": "📅 Today's Clients",
            }

            tool_icons_status = {"pending": "⏳", "done": "✅", "error": "❌"}

            def create_tool_bubble(tool_name: str, content: str = "", call_id: str = None, status: str = "pending"):
                if tool_name is None:
                    return

                title_prefix = tool_titles.get(tool_name, f"🛠️ {tool_name}")

                status_icon = tool_icons_status.get(status, "")
                title = f"{status_icon} {title_prefix}"

                bubble_id = f"tool-{call_id}" if call_id else "tool-noid"

                existing_bubble = None
                for msg in reversed(conversation):
                    if msg.metadata and msg.metadata.get("id") == bubble_id:
                        existing_bubble = msg
                        break

                if existing_bubble:
                    print(f"DEBUG: Updating tool bubble {bubble_id}: Status='{status}', Content='{content[:50]}...'")
                    existing_bubble.metadata["title"] = title
                    existing_bubble.metadata["status"] = status
                    existing_bubble.content = content
                else:
                    print(f"DEBUG: Creating tool bubble {bubble_id}: Status='{status}', Content='{content[:50]}...'")
                    msg = ChatMessage(
                        role="assistant", content=content, metadata={"title": title, "id": bubble_id, "status": status}
                    )
                    conversation.append(msg)

                return msg

            event_handler = EventHandler(tracer)
            event_handler.conversation = conversation
            event_handler.create_tool_bubble_fn = create_tool_bubble

            print(f"Starting agent stream for thread {thread.id}...")
            try:
                with project_client.agents.create_stream(
                    thread_id=thread.id,
                    assistant_id=agent.id,
                    event_handler=event_handler,
                ) as stream:
                    for item in stream:
                        try:
                            event_type, event_data, *_ = item

                            if event_type == "thread.run.step.delta":
                                pass

                            elif event_type == "run_step":
                                pass

                            elif event_type == "thread.message.delta":
                                pass

                            elif event_type == "thread_run":
                                status = event_data.get("status")
                                print(f"\nthread_run status > {status} (ID: {event_data.get('id')})")

                                if status == "requires_action":
                                    print("⚠️ NOTE: Run requires action - this is normal for tool calls")
                                elif status == "failed":
                                    print(f"❌ ERROR > Run failed with ID: {event_data.get('id')}")
                                    if "last_error" in event_data and event_data["last_error"]:
                                        print(f"❌ ERROR DETAILS > {event_data['last_error']}")

                            yield [convert_chatmessage_to_dict(m) for m in conversation], ""

                        except Exception as stream_item_ex:
                            print(f"❌ ERROR processing stream item: {stream_item_ex}")
                            continue

                print("Agent stream finished successfully.")
            except Exception as stream_ex:
                print(f"❌ ERROR in stream: {stream_ex}")
                error_msg = ChatMessage(
                    role="assistant", content=f"An error occurred while processing your request: {str(stream_ex)}"
                )
                conversation.append(error_msg)

            yield [convert_chatmessage_to_dict(m) for m in conversation], ""

        except Exception as e:
            print(f"❌ CRITICAL ERROR in chat execution: {e}")
            error_msg = ChatMessage(
                role="assistant",
                content=f"An error occurred: {str(e)}. Please try again or contact support if the issue persists.",
            )
            conversation.append(error_msg)
            if chat_span and hasattr(chat_span, "is_recording") and chat_span.is_recording():
                try:
                    chat_span.record_exception(e)
                    chat_span.set_status(trace.Status(trace.StatusCode.ERROR, description=str(e)))
                except Exception as trace_ex:
                    print(f"WARNING: Error recording exception in span: {trace_ex}")
            yield [convert_chatmessage_to_dict(m) for m in conversation], ""

        finally:
            if chat_span and hasattr(chat_span, "end"):
                if hasattr(chat_span, "is_recording") and chat_span.is_recording():
                    chat_span.set_attribute("conversation_length_end", len(conversation))
                    if (
                        hasattr(chat_span, "status")
                        and not chat_span.status.is_ok
                        and chat_span.status.status_code != trace.StatusCode.ERROR
                    ):
                        chat_span.set_status(trace.Status(trace.StatusCode.OK))
                chat_span.end()
                print("Chat interaction span ended.")

    return azure_store_chat
