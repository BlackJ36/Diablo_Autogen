from langchain_openai import ChatOpenAI
from langchain_community.tools import DuckDuckGoSearchResults
llm = ChatOpenAI(openai_api_base="https://oneapi.xty.app/v1",openai_api_key="sk-OqlsJwGTMdD1ujTG02Bb0fE08b7f4b30B07d8e83012bA8A8")
llm.invoke("how can langsmith help with testing?")
DuckDuckGoSearchResults(
    name="duck_duck_go"
)