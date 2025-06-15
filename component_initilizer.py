from langchain_openai import AzureChatOpenAI
from langchain_pinecone import PineconeVectorStore
from pinecone import Pinecone
from langchain_openai.embeddings import OpenAIEmbeddings
import logging
# from langchain.tools.tavily_search import TavilySearchResults
logger = logging.getLogger(__name__)
import os
from dotenv import load_dotenv

load_dotenv()

OPENAI_API_KEY=os.environ["OPENAI_API_KEY"] 
AZURE_OPENAI_API_KEY=os.environ["AZURE_OPENAI_API_KEY"]
os.environ["OPENAI_API_VERSION"]="2024-08-01-preview"
AZURE_OPENAI_ENDPOINT=os.environ["AZURE_OPENAI_ENDPOINT"]

llm = AzureChatOpenAI(
    azure_deployment="Alfred-gpt-4o",
    api_version=os.environ.get("OPENAI_API_VERSION", "2024-08-01-preview"),  # Default version if not set
    temperature=0,
    max_tokens=None,)