from flask import Flask, request, jsonify
from tavily import TavilyClient
import os
from flask_cors import CORS

app = Flask(__name__)
CORS(app)  # Enable CORS for Streamlit integration

# Initialize Tavily client
from dotenv import load_dotenv

load_dotenv()  # Loads variables from .env into environment

TAVILY_API_KEY = os.getenv("TAVILY_API_KEY")
client = TavilyClient(TAVILY_API_KEY)

# Andhra Pradesh Government Domains
AP_GOV_DOMAINS = [
    "ap.gov.in",
    "apland.ap.gov.in",
    "webland.ap.gov.in",
    "registration.ap.gov.in",
    "aponline.ap.gov.in",
    "appolice.gov.in",
    "aptransport.org",
    "aphrdi.ap.gov.in",
    "apgenco.gov.in",
    "aptransco.gov.in",
    "apspdcl.in",
    "apepdcl.in",
    "apcpdcl.gov.in",
    "apssb.gov.in",
    "appsc.gov.in",
    "aptet.apcfss.in",
    "school9.ap.gov.in",
    "apfinance.gov.in",
    "apwater.gov.in",
    "aphorticulture.gov.in",
    "apagri.gov.in",
    "apforest.gov.in",
    "aptourism.gov.in",
    "apithelp.gov.in",
    "webland.ap.gov.in",
    "village.ap.gov.in",
    "creditplus.ap.gov.in",
    "epass.ap.gov.in",
    "apmepma.gov.in",
    "appost.in",
    "andhrapradesh.gov.in"
]

# System instruction for summarization
SYSTEM_INSTRUCTION = """
You are a helpful AI assistant that summarizes search results from Andhra Pradesh government websites.
Your task is to:
1. Analyze the search results from AP government sources and extract relevant information
2. Provide a clear, concise summary that directly answers the user's question
3. Focus on the most important and relevant details from official AP government sources
4. Maintain accuracy and avoid speculation
5. If information is insufficient from AP government sources, acknowledge the limitations
6. Always mention that the information is from Andhra Pradesh government sources
"""

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
        max_results = data.get('max_results', 5)
        
        # Get search scope from request, default to AP Gov only
        search_scope = data.get('search_scope', 'ap_gov_only')
        
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
        
        # Generate summary response
        if response.get('answer') and search_scope != 'ap_gov_only':
            # Use Tavily's built-in answer if available and not restricting to AP gov only
            summary_response = response['answer']
        else:
            # Create summary from results
            summary_parts = []
            for result in high_confidence_results[:3]:  # Top 3 results
                if result.get('content'):
                    summary_parts.append(result['content'][:300] + "...")
            
            if summary_parts:
                summary_response = " ".join(summary_parts)
                if search_scope == 'ap_gov_only':
                    summary_response = f"Based on Andhra Pradesh government sources: {summary_response}"
            else:
                summary_response = "Sorry, could not find any relevant data from the specified sources"
        
        # Prepare final response
        if sources:
            final_response = {
                "response": summary_response,
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