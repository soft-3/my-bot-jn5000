"""
JN5000 Ultimate - Streamlit Edition
Multi-Platform Live Streaming Command Center

A simplified, single-file version for easy deployment on Streamlit Cloud.
Features: Twitch integration, Groq AI, Translation, Real-time chat display
"""

import streamlit as st
import asyncio
from datetime import datetime
import time
from typing import Optional, Dict, List
import re

# Try importing optional dependencies
try:
    from twitchio.ext import commands
    TWITCH_AVAILABLE = True
except ImportError:
    TWITCH_AVAILABLE = False
    st.warning("⚠️ TwitchIO not installed. Twitch features will be limited.")

try:
    from groq import Groq
    GROQ_AVAILABLE = True
except ImportError:
    GROQ_AVAILABLE = False
    st.warning("⚠️ Groq not installed. AI features will be limited.")

try:
    from googletrans import Translator
    TRANSLATION_AVAILABLE = True
except ImportError:
    TRANSLATION_AVAILABLE = False
    st.warning("⚠️ Googletrans not installed. Translation features will be limited.")


# ============================================================================
# CONFIGURATION
# ============================================================================

st.set_page_config(
    page_title="JN5000 Ultimate",
    page_icon="🎮",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Custom CSS for better styling
st.markdown("""
<style>
    .main-header {
        font-size: 2.5rem;
        font-weight: bold;
        background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
        -webkit-background-clip: text;
        -webkit-text-fill-color: transparent;
        margin-bottom: 1rem;
    }
    .message-box {
        padding: 1rem;
        border-radius: 10px;
        margin-bottom: 0.5rem;
        border-left: 4px solid;
    }
    .twitch-msg {
        background-color: #f0e6ff;
        border-left-color: #9146ff;
    }
    .translation-msg {
        background-color: #e6f7ff;
        border-left-color: #1890ff;
    }
    .ai-msg {
        background-color: #e6ffe6;
        border-left-color: #52c41a;
    }
    .system-msg {
        background-color: #fff7e6;
        border-left-color: #faad14;
    }
    .stat-card {
        padding: 1rem;
        border-radius: 10px;
        background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
        color: white;
        text-align: center;
    }
</style>
""", unsafe_allow_html=True)


# ============================================================================
# SESSION STATE INITIALIZATION
# ============================================================================

if 'messages' not in st.session_state:
    st.session_state.messages = []

if 'system_running' not in st.session_state:
    st.session_state.system_running = False

if 'twitch_bot' not in st.session_state:
    st.session_state.twitch_bot = None

if 'message_count' not in st.session_state:
    st.session_state.message_count = 0

if 'translation_count' not in st.session_state:
    st.session_state.translation_count = 0

if 'ai_response_count' not in st.session_state:
    st.session_state.ai_response_count = 0


# ============================================================================
# TWITCH BOT CLASS
# ============================================================================

if TWITCH_AVAILABLE:
    class JN5000Bot(commands.Bot):
        def __init__(self, token: str, prefix: str, initial_channels: List[str], 
                     groq_client: Optional[any], translator: Optional[any],
                     settings: Dict):
            super().__init__(token=token, prefix=prefix, initial_channels=initial_channels)
            self.groq_client = groq_client
            self.translator = translator
            self.settings = settings

        async def event_ready(self):
            """Called when bot is ready"""
            st.session_state.messages.append({
                'type': 'system',
                'username': 'SystemBot',
                'message': f'✅ Connected to Twitch as {self.nick}',
                'timestamp': datetime.now()
            })
            st.session_state.message_count += 1

        async def event_message(self, message):
            """Called when a message is received"""
            # Ignore messages from the bot itself
            if message.echo:
                return

            # Add original message
            st.session_state.messages.append({
                'type': 'twitch',
                'username': message.author.name,
                'message': message.content,
                'timestamp': datetime.now()
            })
            st.session_state.message_count += 1

            # Translation
            if self.settings.get('translation_enabled') and self.translator:
                try:
                    translated = self.translator.translate(
                        message.content,
                        dest=self.settings.get('target_language', 'ar')
                    )
                    st.session_state.messages.append({
                        'type': 'translation',
                        'username': 'Translator',
                        'message': f"📝 {translated.text}",
                        'timestamp': datetime.now()
                    })
                    st.session_state.translation_count += 1
                except Exception as e:
                    print(f"Translation error: {e}")

            # AI Response
            if self.settings.get('ai_enabled') and self.groq_client:
                try:
                    response = await self.generate_ai_response(
                        message.author.name,
                        message.content
                    )
                    if response:
                        st.session_state.messages.append({
                            'type': 'ai',
                            'username': 'AI Bot',
                            'message': f"🤖 @{message.author.name}: {response}",
                            'timestamp': datetime.now()
                        })
                        st.session_state.ai_response_count += 1
                        
                        # Send response to chat
                        channel = message.channel
                        await channel.send(f"@{message.author.name} {response}")
                except Exception as e:
                    print(f"AI error: {e}")

        async def generate_ai_response(self, username: str, message: str) -> Optional[str]:
            """Generate AI response using Groq"""
            try:
                # Build system message from profile
                profile = self.settings.get('profile', {})
                system_message = f"""You are {profile.get('nickname', 'a streamer')}.
Bio: {profile.get('bio', 'A friendly streamer')}
Style: {profile.get('style', 'Friendly and helpful')}
Current Game: {profile.get('game', 'Various games')}
Setup: CPU: {profile.get('cpu', 'N/A')}, GPU: {profile.get('gpu', 'N/A')}

Respond naturally and briefly (1-2 sentences) to viewer messages.
Be friendly, engaging, and stay in character."""

                completion = self.groq_client.chat.completions.create(
                    messages=[
                        {"role": "system", "content": system_message},
                        {"role": "user", "content": f"{username} says: {message}"}
                    ],
                    model="llama-3.1-70b-versatile",
                    temperature=0.7,
                    max_tokens=150
                )
                
                return completion.choices[0].message.content.strip()
            except Exception as e:
                print(f"Groq API error: {e}")
                return None


# ============================================================================
# HELPER FUNCTIONS
# ============================================================================

def add_system_message(message: str):
    """Add a system message"""
    st.session_state.messages.append({
        'type': 'system',
        'username': 'SystemBot',
        'message': message,
        'timestamp': datetime.now()
    })
    st.session_state.message_count += 1


def clear_messages():
    """Clear all messages"""
    st.session_state.messages = []
    st.session_state.message_count = 0
    st.session_state.translation_count = 0
    st.session_state.ai_response_count = 0


def format_timestamp(dt: datetime) -> str:
    """Format timestamp"""
    return dt.strftime("%H:%M:%S")


def render_message(msg: Dict):
    """Render a single message"""
    msg_type = msg['type']
    username = msg['username']
    content = msg['message']
    timestamp = format_timestamp(msg['timestamp'])
    
    css_class = f"{msg_type}-msg"
    
    st.markdown(f"""
    <div class="message-box {css_class}">
        <strong>{username}</strong> <small>({timestamp})</small><br>
        {content}
    </div>
    """, unsafe_allow_html=True)


# ============================================================================
# SIDEBAR - CONFIGURATION
# ============================================================================

with st.sidebar:
    st.markdown('<h1 class="main-header">⚙️ Settings</h1>', unsafe_allow_html=True)
    
    # Twitch Configuration
    st.subheader("🟣 Twitch Configuration")
    twitch_channel = st.text_input(
        "Channel Name",
        value="",
        help="Your Twitch channel name (without @)"
    )
    twitch_token = st.text_input(
        "OAuth Token",
        value="",
        type="password",
        help="Get from https://twitchapps.com/tmi/"
    )
    twitch_bot_name = st.text_input(
        "Bot Username",
        value="",
        help="Your bot's Twitch username"
    )
    
    st.markdown("---")
    
    # AI Configuration
    st.subheader("🤖 AI Configuration")
    ai_enabled = st.checkbox("Enable AI Responses", value=True)
    groq_api_key = st.text_input(
        "Groq API Key",
        value="",
        type="password",
        help="Get free key from https://console.groq.com"
    )
    
    st.markdown("---")
    
    # Translation Configuration
    st.subheader("🌍 Translation")
    translation_enabled = st.checkbox("Enable Translation", value=True)
    target_language = st.selectbox(
        "Target Language",
        options=['ar', 'en', 'es', 'fr', 'de', 'it', 'pt', 'ru', 'ja', 'ko', 'zh-cn'],
        format_func=lambda x: {
            'ar': '🇸🇦 Arabic',
            'en': '🇺🇸 English',
            'es': '🇪🇸 Spanish',
            'fr': '🇫🇷 French',
            'de': '🇩🇪 German',
            'it': '🇮🇹 Italian',
            'pt': '🇵🇹 Portuguese',
            'ru': '🇷🇺 Russian',
            'ja': '🇯🇵 Japanese',
            'ko': '🇰🇷 Korean',
            'zh-cn': '🇨🇳 Chinese'
        }[x]
    )
    
    st.markdown("---")
    
    # Profile Configuration
    st.subheader("👤 Profile")
    with st.expander("Profile Settings"):
        nickname = st.text_input("Nickname", value="Streamer")
        bio = st.text_area("Bio", value="A friendly streamer")
        style = st.text_input("Style", value="Friendly and helpful")
        game = st.text_input("Current Game", value="Various games")
        cpu = st.text_input("CPU", value="Intel i9")
        gpu = st.text_input("GPU", value="RTX 4090")
    
    st.markdown("---")
    
    # System Controls
    st.subheader("🎮 System Controls")
    
    col1, col2 = st.columns(2)
    
    with col1:
        if st.button("🗑️ Clear Messages", use_container_width=True):
            clear_messages()
            st.rerun()
    
    with col2:
        if st.button("🔄 Refresh", use_container_width=True):
            st.rerun()


# ============================================================================
# MAIN AREA
# ============================================================================

# Header
st.markdown('<h1 class="main-header">🎮 JN5000 Ultimate - Streamlit Edition</h1>', unsafe_allow_html=True)
st.markdown("**Multi-Platform Live Streaming Command Center**")

# Statistics
col1, col2, col3, col4 = st.columns(4)

with col1:
    st.markdown(f"""
    <div class="stat-card">
        <h3>{st.session_state.message_count}</h3>
        <p>Total Messages</p>
    </div>
    """, unsafe_allow_html=True)

with col2:
    st.markdown(f"""
    <div class="stat-card">
        <h3>{st.session_state.translation_count}</h3>
        <p>Translations</p>
    </div>
    """, unsafe_allow_html=True)

with col3:
    st.markdown(f"""
    <div class="stat-card">
        <h3>{st.session_state.ai_response_count}</h3>
        <p>AI Responses</p>
    </div>
    """, unsafe_allow_html=True)

with col4:
    status = "🟢 Running" if st.session_state.system_running else "🔴 Stopped"
    st.markdown(f"""
    <div class="stat-card">
        <h3>{status}</h3>
        <p>System Status</p>
    </div>
    """, unsafe_allow_html=True)

st.markdown("---")

# Start/Stop System
col1, col2, col3 = st.columns([1, 2, 1])

with col2:
    if not st.session_state.system_running:
        if st.button("▶️ Start System", use_container_width=True, type="primary"):
            # Validate configuration
            if not twitch_channel or not twitch_token or not twitch_bot_name:
                st.error("❌ Please fill in all Twitch configuration fields!")
            elif not TWITCH_AVAILABLE:
                st.error("❌ TwitchIO is not installed. Please install it first.")
            else:
                try:
                    # Initialize Groq client
                    groq_client = None
                    if ai_enabled and groq_api_key and GROQ_AVAILABLE:
                        groq_client = Groq(api_key=groq_api_key)
                    
                    # Initialize Translator
                    translator = None
                    if translation_enabled and TRANSLATION_AVAILABLE:
                        translator = Translator()
                    
                    # Prepare settings
                    settings = {
                        'translation_enabled': translation_enabled,
                        'target_language': target_language,
                        'ai_enabled': ai_enabled,
                        'profile': {
                            'nickname': nickname,
                            'bio': bio,
                            'style': style,
                            'game': game,
                            'cpu': cpu,
                            'gpu': gpu
                        }
                    }
                    
                    # Create bot instance
                    bot = JN5000Bot(
                        token=twitch_token,
                        prefix='!',
                        initial_channels=[twitch_channel],
                        groq_client=groq_client,
                        translator=translator,
                        settings=settings
                    )
                    
                    st.session_state.twitch_bot = bot
                    st.session_state.system_running = True
                    
                    add_system_message("🎮 System started! Connecting to Twitch...")
                    
                    # Start bot in background
                    import threading
                    def run_bot():
                        try:
                            bot.run()
                        except Exception as e:
                            add_system_message(f"❌ Error: {str(e)}")
                            st.session_state.system_running = False
                    
                    thread = threading.Thread(target=run_bot, daemon=True)
                    thread.start()
                    
                    st.success("✅ System started successfully!")
                    time.sleep(1)
                    st.rerun()
                    
                except Exception as e:
                    st.error(f"❌ Failed to start system: {str(e)}")
    else:
        if st.button("⏹️ Stop System", use_container_width=True, type="secondary"):
            if st.session_state.twitch_bot:
                try:
                    # Stop the bot
                    st.session_state.twitch_bot.close()
                except:
                    pass
            
            st.session_state.twitch_bot = None
            st.session_state.system_running = False
            add_system_message("⏹️ System stopped")
            st.success("✅ System stopped successfully!")
            time.sleep(1)
            st.rerun()

st.markdown("---")

# Messages Display
st.subheader("💬 Live Messages")

# Auto-refresh
if st.session_state.system_running:
    st.info("🔄 Auto-refreshing every 2 seconds...")
    time.sleep(2)
    st.rerun()

# Display messages (most recent first)
if st.session_state.messages:
    messages_container = st.container()
    with messages_container:
        for msg in reversed(st.session_state.messages[-50:]):  # Show last 50 messages
            render_message(msg)
else:
    st.info("👋 No messages yet. Start the system and write something in your Twitch chat!")

# Footer
st.markdown("---")
st.markdown("""
<div style="text-align: center; color: #666; padding: 2rem;">
    <p><strong>JN5000 Ultimate - Streamlit Edition</strong></p>
    <p>Multi-Platform Live Streaming Command Center</p>
    <p>Version 2.0.0 | Made with ❤️ using Streamlit</p>
</div>
""", unsafe_allow_html=True)


# ============================================================================
# INSTRUCTIONS (Shown when system is not running)
# ============================================================================

if not st.session_state.system_running and not st.session_state.messages:
    st.markdown("---")
    st.subheader("📋 Quick Start Guide")
    
    col1, col2 = st.columns(2)
    
    with col1:
        st.markdown("""
        ### 🔑 Get API Keys
        
        **1. Twitch OAuth Token** (Required)
        - Go to: [twitchapps.com/tmi](https://twitchapps.com/tmi/)
        - Login with your bot account
        - Click "Connect"
        - Copy the token (starts with `oauth:`)
        
        **2. Groq API Key** (Optional - for AI)
        - Go to: [console.groq.com](https://console.groq.com)
        - Sign up (FREE!)
        - Create API Key
        - Copy the key (starts with `gsk_`)
        """)
    
    with col2:
        st.markdown("""
        ### 🚀 How to Use
        
        **1. Configure Settings**
        - Fill in Twitch credentials in sidebar
        - Add Groq API key (optional)
        - Configure translation settings
        - Fill in your profile information
        
        **2. Start System**
        - Click "▶️ Start System" button
        - Wait for connection confirmation
        
        **3. Test**
        - Write a message in your Twitch chat
        - Watch it appear here in real-time!
        - See translation and AI response
        """)
    
    st.markdown("---")
    
    st.info("""
    💡 **Tips:**
    - Make sure your Twitch bot account is a moderator in your channel
    - The system will auto-refresh every 2 seconds when running
    - AI responses are sent back to your Twitch chat automatically
    - Translation supports 11+ languages
    """)
