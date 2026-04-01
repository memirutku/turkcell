"""AgentService: LangGraph StateGraph agent for multi-step telecom workflows.

Orchestrates the full agent workflow: context gathering, LLM reasoning with
tool calling, action proposal via interrupt()-based confirmation, and action
execution against MockBSSService.

Streams tokens via SSE during reasoning/response generation. Pauses at
confirmation step via interrupt() and emits action_proposal SSE event.
POST /api/agent/confirm resumes the graph with user's approval/rejection.
"""

import json
import logging
from collections.abc import AsyncIterator
from typing import Any

from langchain_core.messages import AIMessage, HumanMessage, SystemMessage, ToolMessage
from langchain_google_genai import ChatGoogleGenerativeAI
from langgraph.checkpoint.memory import MemorySaver
from langgraph.graph import END, START, StateGraph
from langgraph.prebuilt import ToolNode
from langgraph.types import Command, interrupt

from app.config import Settings
from app.models.agent_schemas import AgentState
from app.prompts.agent_prompts import AGENT_SYSTEM_PROMPT
from app.services.agent_tools import get_telecom_tools
from app.services.billing_context import BillingContextService
from app.services.mock_bss import MockBSSService
from app.services.pii_service import PIIMaskingService
from app.services.rag_service import RAGService

logger = logging.getLogger(__name__)

# Tool names that require user confirmation before execution
_ACTION_TOOLS = {"activate_package", "change_tariff"}


class AgentService:
    """LangGraph StateGraph agent for Turkcell telecom workflows.

    Nodes:
      - gather_context: RAG search + billing context + PII masking
      - agent: Gemini LLM with tool bindings
      - tools: ToolNode for non-destructive tool execution (lookup, list)
      - propose_action: interrupt() for user confirmation on destructive actions
      - execute_action: Execute confirmed action against MockBSS

    The graph uses MemorySaver checkpointer to persist state across
    the confirmation round-trip (stream -> interrupt -> resume).
    """

    def __init__(
        self,
        settings: Settings,
        mock_bss: MockBSSService,
        billing_context: BillingContextService,
        pii_enabled: bool = True,
    ) -> None:
        self._mock_bss = mock_bss
        self._tools = get_telecom_tools(mock_bss)

        # LLM with tools bound for function calling
        llm = ChatGoogleGenerativeAI(
            model="gemini-2.0-flash",
            google_api_key=settings.gemini_api_key,
            temperature=0.3,
        )
        self._llm = llm.bind_tools(self._tools)

        # Plain LLM for general chat (no tool binding)
        self._llm_plain = ChatGoogleGenerativeAI(
            model="gemini-2.0-flash",
            google_api_key=settings.gemini_api_key,
            temperature=0.3,
        )

        self._checkpointer = MemorySaver()
        self._rag = RAGService(settings)
        self._billing_context = billing_context
        self._pii_service = PIIMaskingService() if pii_enabled else None

        self._graph = self._build_graph()

    def _build_graph(self):
        """Build and compile the LangGraph StateGraph."""
        builder = StateGraph(AgentState)

        builder.add_node("gather_context", self._gather_context_node)
        builder.add_node("agent", self._agent_node)
        builder.add_node("tools", ToolNode(self._tools))
        builder.add_node("propose_action", self._propose_action_node)
        builder.add_node("execute_action", self._execute_action_node)

        builder.add_edge(START, "gather_context")
        builder.add_edge("gather_context", "agent")
        builder.add_conditional_edges("agent", self._route_after_agent)
        builder.add_edge("tools", "agent")
        # propose_action and execute_action use Command for routing

        return builder.compile(checkpointer=self._checkpointer)

    # -- Graph nodes --

    async def _gather_context_node(self, state: AgentState) -> dict:
        """Gather RAG context and billing context for the agent."""
        customer_id = state.get("customer_id")
        messages = state["messages"]

        # Get the last user message for RAG search
        user_message = ""
        for msg in reversed(messages):
            if isinstance(msg, HumanMessage):
                user_message = msg.content
                break

        # Apply PII masking to user message before RAG search
        masked_message = user_message
        if self._pii_service and user_message:
            masked_message = self._pii_service.mask(user_message)

        # RAG search
        rag_context = ""
        try:
            results = await self._rag.search(masked_message, top_k=5)
            if results:
                rag_context = "\n\n".join(r["content"] for r in results)
        except Exception as e:
            logger.warning("RAG search failed in agent: %s", e)
            rag_context = ""

        # Billing context
        customer_context = ""
        if customer_id:
            customer_context = self._billing_context.get_customer_context(customer_id) or ""

        # Format system prompt with context
        system_content = AGENT_SYSTEM_PROMPT.format(
            customer_context=customer_context or "Musteri bilgisi mevcut degil.",
            rag_context=rag_context or "Bilgi kaynaklarinda ilgili bilgi bulunamadi.",
        )

        return {
            "rag_context": rag_context,
            "customer_context": customer_context,
            "messages": [SystemMessage(content=system_content)],
        }

    async def _agent_node(self, state: AgentState) -> dict:
        """Invoke the LLM with tool bindings."""
        response = await self._llm.ainvoke(state["messages"])
        return {"messages": [response]}

    def _route_after_agent(self, state: AgentState) -> str:
        """Route based on the LLM's response: tools, propose_action, or END."""
        last_message = state["messages"][-1]

        if hasattr(last_message, "tool_calls") and last_message.tool_calls:
            # Check if any tool call is a destructive action
            has_action_tool = any(
                tc["name"] in _ACTION_TOOLS for tc in last_message.tool_calls
            )
            if has_action_tool:
                return "propose_action"
            # Non-destructive tools (lookup, list) -- execute directly
            return "tools"

        # No tool calls -- general chat response, we're done
        return END

    async def _propose_action_node(self, state: AgentState) -> Command:
        """Propose an action and wait for user confirmation via interrupt()."""
        # Find the last AIMessage with tool calls
        last_ai_message = None
        for msg in reversed(state["messages"]):
            if isinstance(msg, AIMessage) and hasattr(msg, "tool_calls") and msg.tool_calls:
                last_ai_message = msg
                break

        if not last_ai_message:
            return Command(goto=END, update={
                "messages": [AIMessage(content="Bir sorun olustu, islem bulunamadi.")],
            })

        # Extract the action tool call
        tool_call = next(
            (tc for tc in last_ai_message.tool_calls if tc["name"] in _ACTION_TOOLS),
            None,
        )
        if not tool_call:
            return Command(goto=END, update={
                "messages": [AIMessage(content="Bir sorun olustu, islem bulunamadi.")],
            })

        tool_name = tool_call["name"]
        tool_args = tool_call["args"]

        # Build action description
        if tool_name == "activate_package":
            action_type = "package_activation"
            package = self._mock_bss.get_package(tool_args.get("package_id", ""))
            package_name = package.name if package else tool_args.get("package_id", "Bilinmeyen paket")
            price = str(package.price_tl) + " TL" if package else "Bilinmiyor"
            description = f"{package_name} paketini tanimlamak istiyor musunuz?"
            details = {
                "customer_id": tool_args.get("customer_id", ""),
                "package_id": tool_args.get("package_id", ""),
                "package_name": package_name,
                "price": price,
            }
        else:  # change_tariff
            action_type = "tariff_change"
            customer_id = tool_args.get("customer_id", "")
            new_tariff_id = tool_args.get("new_tariff_id", "")
            customer = self._mock_bss.get_customer(customer_id)
            current_tariff = customer.tariff if customer else None
            new_tariff = self._mock_bss.get_tariff(new_tariff_id)

            current_name = current_tariff.name if current_tariff else "Bilinmiyor"
            new_name = new_tariff.name if new_tariff else new_tariff_id
            description = f"Tarifinizi {current_name} -> {new_name} olarak degistirmek istiyor musunuz?"
            details = {
                "customer_id": customer_id,
                "new_tariff_id": new_tariff_id,
                "current_tariff": current_name,
                "new_tariff": new_name,
            }

        proposal = {
            "action_type": action_type,
            "description": description,
            "details": details,
        }

        # CRITICAL: interrupt() pauses the graph and sends proposal to frontend
        # Code AFTER interrupt() executes ONLY on resume (Pitfall 1)
        user_response = interrupt(proposal)

        # After resume: check user's decision
        if user_response.get("approved"):
            return Command(goto="execute_action", update={"proposed_action": proposal})
        else:
            return Command(
                goto=END,
                update={
                    "messages": [
                        AIMessage(content="Anlasildi, islem iptal edildi. Baska bir konuda yardimci olabilir miyim?"),
                    ],
                    "action_result": {
                        "status": "cancelled",
                        "action_type": action_type,
                    },
                },
            )

    async def _execute_action_node(self, state: AgentState) -> dict:
        """Execute the confirmed action against MockBSS."""
        # Find the last AIMessage with the action tool call
        tool_call = None
        for msg in reversed(state["messages"]):
            if isinstance(msg, AIMessage) and hasattr(msg, "tool_calls") and msg.tool_calls:
                for tc in msg.tool_calls:
                    if tc["name"] in _ACTION_TOOLS:
                        tool_call = tc
                        break
                if tool_call:
                    break

        if not tool_call:
            return {
                "messages": [AIMessage(content="Islem gerceklestirilemedi. Lutfen tekrar deneyin.")],
                "action_result": {"status": "error", "error": "Tool call not found"},
            }

        tool_name = tool_call["name"]
        tool_args = tool_call["args"]

        try:
            if tool_name == "activate_package":
                result = await self._mock_bss.activate_package(
                    tool_args["customer_id"],
                    tool_args["package_id"],
                )
            else:  # change_tariff
                result = await self._mock_bss.change_tariff(
                    tool_args["customer_id"],
                    tool_args["new_tariff_id"],
                )

            if result.get("success"):
                result_message = result.get("message_tr", "Islem basariyla tamamlandi.")
            else:
                result_message = f"Islem basarisiz: {result.get('error', 'Bilinmeyen hata')}"

            return {
                "messages": [AIMessage(content=result_message)],
                "action_result": result,
            }
        except Exception as e:
            logger.error("Action execution failed: %s", e, exc_info=True)
            return {
                "messages": [AIMessage(content="Islem sirasinda bir hata olustu. Lutfen tekrar deneyin.")],
                "action_result": {"status": "error", "error": str(e)},
            }

    # -- Public streaming methods --

    async def stream(self, message: str, session_id: str, customer_id: str) -> AsyncIterator[dict]:
        """Stream agent response events for a user message.

        Yields dicts with type: "token", "action_proposal", "action_result", "error".

        For action-requiring requests:
        1. Streams reasoning tokens
        2. Emits action_proposal event
        3. CLOSES the SSE stream (does NOT keep connection open during confirmation)

        Frontend then sends POST /api/agent/confirm to resume.

        Args:
            message: User's message in Turkish.
            session_id: Session ID (used as LangGraph thread_id).
            customer_id: Customer ID for billing context.
        """
        config = {"configurable": {"thread_id": session_id}}
        input_state = {
            "messages": [HumanMessage(content=message)],
            "customer_id": customer_id,
            "session_id": session_id,
            "intent": None,
            "proposed_action": None,
            "action_result": None,
            "rag_context": "",
            "customer_context": "",
        }

        try:
            async for event in self._graph.astream_events(input_state, config=config, version="v2"):
                kind = event["event"]

                # Stream LLM tokens (Pitfall 6: use astream_events v2 with on_chat_model_stream)
                if kind == "on_chat_model_stream":
                    content = event["data"]["chunk"].content
                    if content:
                        yield {"type": "token", "content": content}

            # After stream completes, check for interrupt state
            graph_state = self._graph.get_state(config)
            if graph_state.next:  # Graph has pending nodes (interrupted)
                if graph_state.tasks:
                    for task in graph_state.tasks:
                        if hasattr(task, "interrupts") and task.interrupts:
                            proposal = task.interrupts[0].value
                            proposal["thread_id"] = session_id
                            yield {"type": "action_proposal", "data": proposal}

            # Check for action_result in final state
            final_state = graph_state.values
            if final_state.get("action_result"):
                yield {"type": "action_result", "data": final_state["action_result"]}

        except Exception as e:
            logger.error("Agent stream error: %s", e, exc_info=True)
            yield {"type": "error", "content": "Bir hata olustu. Lutfen tekrar deneyin."}

    async def resume(self, config: dict, user_response: dict) -> AsyncIterator[dict]:
        """Resume the agent graph after user confirmation/rejection.

        Args:
            config: LangGraph config with thread_id ({"configurable": {"thread_id": ...}}).
            user_response: Dict with "approved" key (True/False).

        Yields:
            Dicts with type: "token", "action_result", "error".
        """
        try:
            async for event in self._graph.astream_events(
                Command(resume=user_response), config=config, version="v2"
            ):
                kind = event["event"]
                if kind == "on_chat_model_stream":
                    content = event["data"]["chunk"].content
                    if content:
                        yield {"type": "token", "content": content}

            # Check for action_result in final state
            graph_state = self._graph.get_state(config)
            final_state = graph_state.values
            if final_state.get("action_result"):
                yield {"type": "action_result", "data": final_state["action_result"]}

        except Exception as e:
            logger.error("Agent resume error: %s", e, exc_info=True)
            yield {"type": "error", "content": "Onay islemi sirasinda bir sorun olustu."}
