import os
from dotenv import load_dotenv
load_dotenv()

from typing import TypedDict, Annotated
import operator
import uuid

import psycopg
from psycopg.rows import dict_row

from langgraph.graph import StateGraph,START,END
from langgraph.checkpoint.postgres import PostgresSaver
from langchain_core.messages import (AnyMessage, HumanMessage, AIMessage, SystemMessage)
from langchain_groq import ChatGroq
from tool.tavily_tool import tavily_search, format_results
from tool.flight_tool import get_flight_info, search_flights

def get_database_connection():
    database_url = os.getenv("DATABASE_URL")
    if not database_url:
        raise ValueError("DATABASE_URL environment variable is not set.")
    return database_url

    
GROOQ_API_KEY = os.getenv("GROQ_API_KEY") or os.getenv("GROOQ_API_KEY")
if not GROOQ_API_KEY:
    raise ValueError("GROQ_API_KEY environment variable is not set.")


#===========================
#llm
#==========================

llm = ChatGroq(
    api_key=GROOQ_API_KEY,
    model="openai/gpt-oss-120b",
    max_tokens=1200,
)
# response = llm.invoke([HumanMessage(content="What is the capital of France?")])
# print("Response from ChatGroq:", response.content)

#===========================
# State
#==========================

class TravelState(TypedDict):
    message: Annotated[list[AnyMessage], operator.add]
    user_query: str
    flight_result: str
    hotel_result: str
    itinerary: str
    llm_call: int


def _limit_prompt_context(value: str, max_chars: int) -> str:
    """Keep external search results from overwhelming the model's token budget."""
    value = value or ""
    if len(value) <= max_chars:
        return value
    return value[:max_chars].rstrip() + "\n[Remaining content omitted]"



def flight_agent(state: TravelState) :
    # print("Flight agent called with state:", state)
    # Search for flights based on the user query
    query = state["user_query"]
    # print("Query:", query)
    flight_data= search_flights(query)
    return {"flight_result": flight_data, "message": [AIMessage(content="Flight search results")], "llm_call": state.get("llm_call", 0) + 1}


# print(flight_agent({"user_query": "flights from del to bom"}))

def hotel_agent(state: TravelState) :
    # print("Hotel agent called with state:", state)
    # Search for hotels based on the user query
    query = state["user_query"]
    # print("Query:", query)
    hotel_data= tavily_search(query)
    formatted_hotel_data = format_results(hotel_data)
    return {"hotel_result": formatted_hotel_data, "message": [AIMessage(content="Hotel search results")], "llm_call": state.get("llm_call", 0) + 1}

# print(hotel_agent({"user_query": "Best hotel in india?"}))

def itinerary_agent(state: TravelState) :
    prompt=f"""Generate a practical, budget-friendly and easy-to-follow itinerary based on the user's request and these results.

User request: {_limit_prompt_context(state.get('user_query', ''), 800)}

Flight details:
{_limit_prompt_context(state.get('flight_result', ''), 2200)}

Hotel details:
{_limit_prompt_context(state.get('hotel_result', ''), 2200)}
      """
    response = llm.invoke([
        SystemMessage(content="You are a travel expert agent that generates itineraries based on flight and hotel information."),
        HumanMessage(content=prompt)
        ])
    itinerary = response.content
    return {"itinerary": itinerary, "message": [response], "llm_call": state.get("llm_call", 0) + 1}

def final_agent(state: TravelState) :
    #print("Final agent called with state:", state)
    # Generate final output based on the user query, flight results, hotel results, and itinerary
    final_output = f"""Generate a concise final travel response based on the information below.

User query: {_limit_prompt_context(state.get('user_query', ''), 800)}

Flight results:
{_limit_prompt_context(state.get('flight_result', ''), 1000)}

Hotel results:
{_limit_prompt_context(state.get('hotel_result', ''), 1200)}

Itinerary:
{_limit_prompt_context(state.get('itinerary', ''), 1800)}

    format the final answer beautifully and using these section:
    1.Trip Summary
    2.Flight information
    3.Hotel information
    4.Itinerary
    5. Hotel suggestions
    6.day-by-day itinerary
    7.Estimated budget
    8.Final recommendations

    Important:
    -Be clear and concise in your recommendations.
    -Provide practical advice for the user to have a smooth and enjoyable trip.
    -Mention that live flight API may not provide ticket prices if not available.
    -Keep response user-friendly and easy to understand.
    -Avoid repeating the same details across sections.
    """

    final_llm_response = llm.invoke([
        SystemMessage(content="You are a professional travel agent that provides a comprehensive travel plan based on flight and hotel information."),
        HumanMessage(content=final_output)
        ])
    return {"message": [final_llm_response], "llm_call": state.get("llm_call", 0) + 1}

# ============================

# Build Graph

# ===========================

graph = StateGraph(TravelState)
graph.add_node(flight_agent, name="flight_agent")
graph.add_node(hotel_agent, name="hotel_agent")
graph.add_node(itinerary_agent, name="itinerary_agent")
graph.add_node(final_agent, name="final_agent")

graph.add_edge(START, "flight_agent")
graph.add_edge("flight_agent", "hotel_agent")
graph.add_edge("hotel_agent", "itinerary_agent")
graph.add_edge("itinerary_agent", "final_agent")
graph.add_edge("final_agent", END)

## Save graph to PostgreSQL
database_url = get_database_connection()
_conn= psycopg.connect(database_url, autocommit=True,row_factory=dict_row)
checkpointer= PostgresSaver(_conn)
checkpointer.setup()

travel_graph = graph.compile(checkpointer=checkpointer)

# ============================

# Run Graph

# ============================

def run_travel_agent(user_input: str, thread_id: str = None):
    if not thread_id:
        thread_id= str(uuid.uuid4())

    config={
        "configurable": {
            "thread_id": thread_id
        }
    }
    initial_state: TravelState = {
        "message": [HumanMessage(content=user_input)],
        "user_query": user_input,
        "flight_result": "",
        "hotel_result": "",
        "itinerary": "",
        "llm_call": 0
    }
    result = travel_graph.invoke(initial_state, config=config)
    response=result["message"][-1].content
    return {
        "thread_id": thread_id,
        "response": response,
        "flight_result": result.get("flight_result", ""),
        "hotel_result": result.get("hotel_result", ""),
        "itinerary": result.get("itinerary", ""),
        "llm_call": result.get("llm_call", 0)
    }
