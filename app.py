import streamlit as st
import requests
import speech_recognition as sr
import pyttsx3
import threading
import tempfile
import os
from io import BytesIO
import base64
import time
import wave
import pygame
from gtts import gTTS

# Configure page
st.set_page_config(
    page_title="AP Government Search Assistant",
    page_icon="🏛️",
    layout="wide"
)

# Initialize session state
if 'search_history' not in st.session_state:
    st.session_state.search_history = []
if 'is_listening' not in st.session_state:
    st.session_state.is_listening = False

# API Configuration
API_URL = "http://localhost:8000/search"
DOMAINS_URL = "http://localhost:8000/domains"

def text_to_speech_gtts(text):
    """Convert text to speech using Google Text-to-Speech (gTTS)"""
    try:
        # Create gTTS object
        tts = gTTS(text=text, lang='en', slow=False)
        
        # Save to BytesIO object
        audio_buffer = BytesIO()
        tts.write_to_fp(audio_buffer)
        audio_buffer.seek(0)
        
        return audio_buffer.getvalue()
    except Exception as e:
        st.error(f"Error in Google TTS: {str(e)}")
        return None

def text_to_speech_browser_based(text):
    """Create browser-based text-to-speech using HTML/JavaScript"""
    # This creates an HTML audio element that uses browser's built-in TTS
    html_code = f"""
    <div>
        <button onclick="speakText()" style="
            background-color: #4CAF50;
            border: none;
            color: white;
            padding: 10px 20px;
            text-align: center;
            text-decoration: none;
            display: inline-block;
            font-size: 16px;
            margin: 4px 2px;
            cursor: pointer;
            border-radius: 5px;
        ">🔊 Play Audio</button>
        <button onclick="stopSpeech()" style="
            background-color: #f44336;
            border: none;
            color: white;
            padding: 10px 20px;
            text-align: center;
            text-decoration: none;
            display: inline-block;
            font-size: 16px;
            margin: 4px 2px;
            cursor: pointer;
            border-radius: 5px;
        ">⏹️ Stop</button>
    </div>
    
    <script>
        let utterance = null;
        
        function speakText() {{
            if ('speechSynthesis' in window) {{
                // Cancel any ongoing speech
                speechSynthesis.cancel();
                
                utterance = new SpeechSynthesisUtterance(`{text}`);
                utterance.rate = 0.8;
                utterance.pitch = 1;
                utterance.volume = 1;
                
                speechSynthesis.speak(utterance);
            }} else {{
                alert('Sorry, your browser does not support text-to-speech.');
            }}
        }}
        
        function stopSpeech() {{
            if ('speechSynthesis' in window) {{
                speechSynthesis.cancel();
            }}
        }}
    </script>
    """
    return html_code

def speech_to_text():
    """Convert speech to text using microphone"""
    try:
        r = sr.Recognizer()
        with sr.Microphone() as source:
            st.info("🎤 Listening... Speak now!")
            r.adjust_for_ambient_noise(source, duration=1)
            audio = r.listen(source, timeout=10, phrase_time_limit=10)
        
        st.info("🔄 Processing your speech...")
        text = r.recognize_google(audio)
        return text
    except sr.RequestError as e:
        st.error(f"Could not request results from speech recognition service: {e}")
        return None
    except sr.UnknownValueError:
        st.error("Could not understand the audio. Please try again.")
        return None
    except sr.WaitTimeoutError:
        st.error("Listening timeout. Please try again.")
        return None
    except Exception as e:
        st.error(f"Error in speech recognition: {str(e)}")
        return None

def search_api(query, search_depth="advanced", max_results=5, search_scope="ap_gov_only"):
    """Call the search API"""
    try:
        payload = {
            "query": query,
            "search_depth": search_depth,
            "max_results": max_results,
            "search_scope": search_scope
        }
        
        response = requests.post(API_URL, json=payload, timeout=30)
        
        if response.status_code == 200:
            return response.json()
        else:
            return {
                "error": f"API Error: {response.status_code}",
                "response": "Sorry, could not process your request",
                "source_found": None
            }
    except requests.exceptions.RequestException as e:
        return {
            "error": f"Connection Error: {str(e)}",
            "response": "Sorry, could not connect to the search service",
            "source_found": None
        }

def get_ap_domains():
    """Get list of AP government domains"""
    try:
        response = requests.get(DOMAINS_URL, timeout=10)
        if response.status_code == 200:
            return response.json()
        return None
    except:
        return None

def main():
    st.title("🏛️ Andhra Pradesh Government Search Assistant")
    st.markdown("*Search official information from AP government websites*")
    st.markdown("---")
    
    # Sidebar with domain information
    with st.sidebar:
        st.header("ℹ️ Search Information")
        
        domain_info = get_ap_domains()
        if domain_info:
            st.success(f"Searching across {domain_info['total_domains']} AP Government domains")
            
            with st.expander("View AP Government Domains"):
                for domain in domain_info['ap_government_domains']:
                    st.text(f"• {domain}")
        else:
            st.warning("Could not load domain information")
        
        st.markdown("---")
        st.markdown("**Examples of what you can search:**")
        st.markdown("• Land registration procedures")
        st.markdown("• Government schemes")
        st.markdown("• Online services")
        st.markdown("• Department contacts")
        st.markdown("• Policy documents")
    
    # Create two columns for the main interface
    col1, col2 = st.columns([2, 1])
    
    with col1:
        st.subheader("Search Options")
        
        # Input method selection
        input_method = st.radio(
            "Choose input method:",
            ("Text Input", "Voice Input"),
            horizontal=True
        )
        
        query = ""
        
        if input_method == "Text Input":
            query = st.text_input(
                "Enter your search query:",
                placeholder="e.g., How to apply for land registration in AP?",
                key="text_input"
            )
        
        elif input_method == "Voice Input":
            st.write("Click the button below and speak your query:")
            
            if st.button("🎤 Start Voice Input", type="primary"):
                with st.spinner("Listening for your voice..."):
                    voice_query = speech_to_text()
                    if voice_query:
                        query = voice_query
                        st.success(f"Recognized: '{query}'")
                        st.session_state.voice_query = query
            
            # Display recognized voice input
            if hasattr(st.session_state, 'voice_query'):
                query = st.session_state.voice_query
                st.text_input("Recognized speech:", value=query, disabled=True)
    
    with col2:
        st.subheader("Search Settings")
        
        # Search scope selection
        search_scope = st.selectbox(
            "Search Scope:",
            [
                ("ap_gov_only", "🏛️ AP Government Only"),
                ("include_ap_gov", "🔍 Include AP Gov + Others"),
                ("general", "🌐 General Web Search")
            ],
            format_func=lambda x: x[1],
            index=0
        )[0]
        
        search_depth = st.selectbox(
            "Search Depth:",
            ["basic", "advanced"],
            index=1
        )
        
        max_results = st.slider(
            "Max Results:",
            min_value=1,
            max_value=10,
            value=5
        )
        
        # TTS Method selection
        tts_method = st.selectbox(
            "Text-to-Speech Method:",
            ["Browser TTS", "Google TTS"],
            index=0
        )
    
    # Search button
    col_search, col_clear = st.columns([1, 1])
    
    with col_search:
        search_clicked = st.button("🔍 Search AP Government", type="primary", use_container_width=True)
    
    with col_clear:
        if st.button("🗑️ Clear History", use_container_width=True):
            st.session_state.search_history.clear()
            if hasattr(st.session_state, 'voice_query'):
                del st.session_state.voice_query
            st.rerun()
    
    # Perform search
    if search_clicked and query.strip():
        with st.spinner("Searching AP Government sources..."):
            result = search_api(query, search_depth, max_results, search_scope)
            
            # Store in history
            st.session_state.search_history.append({
                "query": query,
                "result": result,
                "timestamp": time.strftime("%Y-%m-%d %H:%M:%S"),
                "search_scope": search_scope
            })
    
    # Display results
    if st.session_state.search_history:
        st.markdown("---")
        st.subheader("Search Results")
        
        # Show latest result
        latest_search = st.session_state.search_history[-1]
        
        # Display search info
        col_info1, col_info2, col_info3 = st.columns(3)
        with col_info1:
            st.metric("Query", latest_search['query'][:20] + "..." if len(latest_search['query']) > 20 else latest_search['query'])
        with col_info2:
            scope_display = {
                'ap_gov_only': '🏛️ AP Gov Only',
                'include_ap_gov': '🔍 AP Gov + Others', 
                'general': '🌐 General Web'
            }
            st.metric("Search Scope", scope_display.get(latest_search.get('search_scope', 'ap_gov_only')))
        with col_info3:
            st.metric("Results Found", latest_search['result'].get('total_results', 'N/A'))
        
        st.markdown(f"**Search Time:** {latest_search['timestamp']}")
        
        result = latest_search['result']
        
        if "error" in result:
            st.error(f"Error: {result['error']}")
        
        # Display response
        if result.get('response'):
            st.markdown("**📋 Response:**")
            response_text = result['response']
            
            # Highlight if it's from AP government sources
            if result.get('search_scope') == 'ap_gov_only':
                st.info("ℹ️ Information sourced from official Andhra Pradesh government websites")
            
            st.write(response_text)
            
            # Text-to-Speech options
            st.markdown("**🔊 Listen to Response:**")
            
            if tts_method == "Browser TTS":
                # Use browser-based TTS (most reliable)
                st.components.v1.html(
                    text_to_speech_browser_based(response_text),
                    height=100
                )
            
            elif tts_method == "Google TTS":
                if st.button("🔊 Generate Audio", key="gtts_button"):
                    with st.spinner("Converting to speech..."):
                        audio_bytes = text_to_speech_gtts(response_text)
                        if audio_bytes:
                            st.audio(audio_bytes, format="audio/mp3")
            
            # Copy response button
            if st.button("📋 Copy Response", key="copy_button"):
                st.code(response_text, language=None)
        
        # Display sources
        if result.get('source_found'):
            st.markdown("**🔗 Official Sources:**")
            sources = result['source_found'].split(', ')
            for i, source in enumerate(sources, 1):
                # Check if it's an AP government domain
                is_ap_gov = any(domain in source.lower() for domain in [
                    'ap.gov.in', 'apland', 'webland', 'registration.ap.gov.in', 
                    'aponline', 'appolice', 'aptransport', 'appsc', 'aptet'
                ])
                
                icon = "🏛️" if is_ap_gov else "🔗"
                st.markdown(f"{icon} {i}. [{source}]({source})")
        
        # Search History
        if len(st.session_state.search_history) > 1:
            st.markdown("---")
            st.subheader("📚 Search History")
            
            for i, search in enumerate(reversed(st.session_state.search_history[:-1]), 1):
                scope_icon = {
                    'ap_gov_only': '🏛️',
                    'include_ap_gov': '🔍', 
                    'general': '🌐'
                }.get(search.get('search_scope', 'ap_gov_only'), '🔍')
                
                with st.expander(f"{scope_icon} Search {i}: {search['query'][:50]}..."):
                    st.markdown(f"**Time:** {search['timestamp']}")
                    st.markdown(f"**Query:** {search['query']}")
                    st.markdown(f"**Search Scope:** {search.get('search_scope', 'ap_gov_only')}")
                    if search['result'].get('response'):
                        st.markdown("**Response:**")
                        st.write(search['result']['response'])
                    if search['result'].get('source_found'):
                        st.markdown("**Sources:**")
                        st.write(search['result']['source_found'])

if __name__ == "__main__":
    main()