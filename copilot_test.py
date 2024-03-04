# import BaseModel
from pydantic import BaseModel


class Test():
    def __init__(self):
        self.name = "Test"

    def test(self):
        return "Test"

    def test_langchain(BaseModel, Field, BaseTool, CallbackManagerForToolRun, DuckDuckGoSearchAPIWrapper, DDGInput, DuckDuckGoSearchRun, DuckDuckGoSearchResults):
        return (BaseModel, Field, BaseTool, CallbackManagerForToolRun, DuckDuckGoSearchAPIWrapper, DDGInput, DuckDuckGoSearchRun, DuckDuckGoSearchResults)

    # import langchain and complete a agent use tool DuckDukGoSearchResults
    def test_agent(self):
        from langchain_openai import ChatOpenAI
        from langchain_community.tools import DuckDuckGoSearchResults
        llm = ChatOpenAI(openai_api_base="https://oneapi.xty.app/v1",openai_api_key="sk-OqlsJwGTMdD1ujTG02Bb0fE08b7f4b30B07d8e83012bA8A8")
        llm.invoke("how can langsmith help with testing?")
        DuckDuckGoSearchResults(
            name="duck_duck_go"
        )

# use langgraph to create two agent,one can communicate with human input,the other can communicate with the first agent and use search tools
def test_langgraph():
    from langchain_community.agents import LangAgent
    from langchain_core.langgraph import LangGraph
    from langchain_openai import ChatOpenAI
    from langchain_community.tools import DuckDuckGoSearchResults
    llm = ChatOpenAI(openai_api_base="https://oneapi.xty.app/v1",openai_api_key="sk-OqlsJwGTMdD1ujTG02Bb0fE08b7f4b30B07d8e83012bA8A8")
    agent1 = LangAgent(llm)
    agent2 = LangAgent(llm)
    lg = LangGraph()
    lg.add_agent(agent1)
    lg.add_agent(agent2)
    lg.add_edge(agent1, agent2)
    lg.add_edge(agent2, agent1)
    return agent1, agent2, lg

# create a langchain agent has memory and can communicate with agents











