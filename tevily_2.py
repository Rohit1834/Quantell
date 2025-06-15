from flask import Flask, request, jsonify
from tavily import TavilyClient
import os
from flask_cors import CORS

# LLM imports
from langchain_openai import AzureChatOpenAI
from langchain_pinecone import PineconeVectorStore
from pinecone import Pinecone
from langchain_openai.embeddings import OpenAIEmbeddings
from component_initilizer import *
import logging
from dotenv import load_dotenv

load_dotenv()

app = Flask(__name__)
CORS(app)  # Enable CORS for Streamlit integration

# Initialize Tavily client
TAVILY_API_KEY = os.getenv("TAVILY_API_KEY")
client = TavilyClient(TAVILY_API_KEY)

# Initialize LLM
# llm = AzureChatOpenAI(
#     azure_deployment="Alfred-gpt-4o",
#     api_version=os.environ.get("OPENAI_API_VERSION", "2024-08-01-preview"),
#     temperature=0,
#     max_tokens=None,
# )

logger = logging.getLogger(__name__)

# Andhra Pradesh Government Domains
AP_GOV_DOMAINS= [
    # Main portals
    "ap.gov.in",
    "ap.nic.in", 
    "goir.ap.gov.in",
    
    # Police & Law
    "citizen.appolice.gov.in",
    "slprb.ap.gov.in",
    "apsp.ap.gov.in",
    
    # Transport
    "aptransport.org",
    
    # Power
    "apspdcl.in",
    "apeasternpower.com",
    "apcpdcl.in",
    "aperc.gov.in",
    
    # Public Service
    "psc.ap.gov.in",
    "portal-psc.ap.gov.in",
    
    # Agriculture
    "apagrisnet.gov.in",
    "horticulture.ap.nic.in",
    
    # Education
    "schooledu.ap.gov.in",
    "cse.ap.gov.in",
    "aptet.apcfss.in",
    
    # Land & Revenue
    "webland.ap.gov.in",
    
    # Water Resources
    "irrigationap.cgg.gov.in",
    "irrigation.ap.gov.in",
    
    # Forest
    "forests.ap.gov.in",
    
    # Finance
    "apfinance.gov.in",
    
    # Services
    "ap.meeseva.gov.in",
    "apeprocurement.gov.in",
    
    # Information
    "apegazette.cgg.gov.in"
]

# System instruction for LLM
SYSTEM_INSTRUCTION = """
You are a helpful AI assistant that answers questions based on search results from Andhra Pradesh government websites and other sources.

Your task is to:
1. Analyze the provided search results and extract relevant information
2. Provide a clear, comprehensive answer that directly addresses the user's question
3. Focus on the most important and relevant details from the search results
4. Maintain accuracy and avoid speculation beyond what's provided in the search results
5. If information is insufficient, acknowledge the limitations
6. When information comes from AP government sources, mention that it's from official sources
7. Structure your response in a clear, easy-to-understand format
8. Provide step-by-step instructions when applicable

User Query: {query}

Search Results:
{search_results}

Please provide a comprehensive answer based on the above search results.
"""

def generate_llm_response(query, search_results):
    """Generate LLM response based on search results"""
    try:
        # Format search results for LLM
        formatted_results = ""
        for i, result in enumerate(search_results, 1):
            title = result.get('title', 'No title')
            content = result.get('content', 'No content')
            url = result.get('url', 'No URL')
            
            formatted_results += f"""
Result {i}:
Title: {title}
URL: {url}
Content: {content}...

"""
        
        # Create prompt for LLM
        prompt = SYSTEM_INSTRUCTION.format(
            query=query,
            search_results=formatted_results
        )
        
        # Get LLM response
        response = llm.invoke(prompt)
        return response.content
        
    except Exception as e:
        logger.error(f"Error generating LLM response: {str(e)}")
        return f"Sorry, I encountered an error while processing the search results: {str(e)}"

@app.route('/search', methods=['POST'])
def tavily_search():
    try:
        # Get request data
        data = request.get_json()
        
        # Validate required parameters
        if not data or 'query' not in data:
            return jsonify({
                "error": "Query parameter is required"
            }), 400
        
        query = data['query']
        
        # Optional parameters with defaults
        search_depth = data.get('search_depth', 'advanced')  # 'basic' or 'advanced'
        max_results = data.get('max_results', 2)
        
        # Get search scope from request, default to AP Gov only
        search_scope = data.get('search_scope', 'ap_gov_only')
        print("search_scope is >>>>>>>>>>>>>>>>>>",search_scope)
        
        # Set domains based on search scope
        if search_scope == 'ap_gov_only':
            include_domains = AP_GOV_DOMAINS
            exclude_domains = None
        elif search_scope == 'include_ap_gov':
            # Include AP gov domains but also search other sources
            include_domains = None
            exclude_domains = None
        else:  # 'general'
            include_domains = None
            exclude_domains = None
        
        # Add AP/Andhra Pradesh context to query for better results
        if search_scope in ['ap_gov_only', 'include_ap_gov']:
            enhanced_query = f"{query} Andhra Pradesh AP government"
        else:
            enhanced_query = query
        print("enhance search query is >>>>>>>>>>>.",enhanced_query)
        # Perform Tavily search
        response = client.search(
            query=enhanced_query,
            search_depth=search_depth,
            include_answer=True,
            include_raw_content=True,
            max_results=max_results,
            include_domains=include_domains,
            exclude_domains=exclude_domains
        )
        print("response is >>>>>>>>>>>>>>",response)
        
        # Check if results found
        if not response.get('results') or len(response['results']) == 0:
            return jsonify({
                "response": "Sorry, could not find any relevant data from Andhra Pradesh government sources",
                "source_found": None,
                "search_scope": search_scope
            })
        
        # Filter results by confidence score (0.5 threshold for government sites as they might have lower scores)
        confidence_threshold = 0.5 if search_scope == 'ap_gov_only' else 0.75
        high_confidence_results = []
        
        for result in response['results']:
            # Tavily doesn't always provide score, so we'll check if it exists
            score = result.get('score', 1.0)  # Default to 1.0 if no score
            if score >= confidence_threshold:
                high_confidence_results.append(result)
        
        # If no high confidence results, use all results but mention lower confidence
        if not high_confidence_results:
            high_confidence_results = response['results']
        
        # Filter to ensure we only have AP government sources if requested
        if search_scope == 'ap_gov_only':
            ap_gov_results = []
            for result in high_confidence_results:
                url = result.get('url', '')
                if any(domain in url.lower() for domain in AP_GOV_DOMAINS):
                    ap_gov_results.append(result)
            
            if ap_gov_results:
                high_confidence_results = ap_gov_results
            # If no AP gov results found, keep all results but mention this in response
        
        # Extract sources (URLs)
        sources = []
        for result in high_confidence_results:
            if result.get('url'):
                sources.append(result['url'])
        
        # Generate LLM response based on search results
        if high_confidence_results:
            llm_response = generate_llm_response(query, high_confidence_results)
        else:
            llm_response = "Sorry, could not find any relevant data from the specified sources"
        
        # Prepare final response
        if sources:
            final_response = {
                "response": llm_response,
                "source_found": ", ".join(sources),
                "search_scope": search_scope,
                "total_results": len(high_confidence_results)
            }
        else:
            final_response = {
                "response": "Sorry, could not find any relevant data from Andhra Pradesh government sources",
                "source_found": None,
                "search_scope": search_scope,
                "total_results": 0
            }
        
        return jsonify(final_response)
    
    except Exception as e:
        return jsonify({
            "error": f"An error occurred: {str(e)}",
            "response": "Sorry, could not find any relevant data",
            "source_found": None
        }), 500

@app.route('/health', methods=['GET'])
def health_check():
    return jsonify({"status": "healthy", "ap_domains_count": len(AP_GOV_DOMAINS)})

@app.route('/domains', methods=['GET'])
def get_ap_domains():
    """Get list of Andhra Pradesh government domains being searched"""
    return jsonify({
        "ap_government_domains": AP_GOV_DOMAINS,
        "total_domains": len(AP_GOV_DOMAINS)
    })

if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0', port=8000)