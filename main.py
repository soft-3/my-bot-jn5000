import streamlit as st
import asyncio
import threading
from datetime import datetime
import time
from groq import Groq
from googletrans import Translator
from twitchio.ext import commands

# --- إعدادات الصفحة ---
st.set_page_config(page_title="JN5000 Ultimate", page_icon="🎮", layout="wide")

# --- تهيئة الحالة (Session State) ---
if 'messages' not in st.session_state:
    st.session_state.messages = []
if 'running' not in st.session_state:
    st.session_state.running = False

# --- كلاس البوت المطور ---
class JN5000Bot(commands.Bot):
    def __init__(self, token, channel, groq_key):
        super().__init__(token=token, prefix='!', initial_channels=[channel])
        self.groq_client = Groq(api_key=groq_key) if groq_key else None
        self.translator = Translator()

    async def event_ready(self):
        msg = f"✅ المتصل الآن: {self.nick}"
        st.session_state.messages.append({"user": "System", "text": msg, "time": datetime.now().strftime("%H:%M")})

    async def event_message(self, message):
        if message.echo: return
        
        # إضافة الرسالة الأصلية
        st.session_state.messages.append({"user": message.author.name, "text": message.content, "time": datetime.now().strftime("%H:%M")})
        
        # ترجمة فورية (مثال للعربية)
        try:
            trans = self.translator.translate(message.content, dest='ar')
            st.session_state.messages.append({"user": "Translator", "text": f"📝 {trans.text}", "time": ""})
        except: pass

        await self.handle_commands(message)

# --- الواجهة الرسومية ---
st.title("🎮 JN5000 Ultimate v3.0")

with st.sidebar:
    st.header("⚙️ الإعدادات")
    t_channel = st.text_input("اسم القناة (Twitch)")
    t_token = st.text_input("OAuth Token", type="password")
    g_key = st.text_input("Groq API Key", type="password")
    
    if st.button("▶️ تشغيل النظام"):
        if t_channel and t_token:
            st.session_state.running = True
            bot = JN5000Bot(t_token, t_channel, g_key)
            # تشغيل البوت في خلفية مستقرة
            threading.Thread(target=bot.run, daemon=True).start()
            st.success("تم بدء التشغيل!")
        else:
            st.error("أدخل بيانات تويتش أولاً")

# --- عرض الرسائل ---
st.subheader("💬 شات البث المباشر")
for m in reversed(st.session_state.messages[-20:]):
    st.write(f"**{m['user']}**: {m['text']} *{m['time']}*")

# تحديث تلقائي بسيط
if st.session_state.running:
    time.sleep(2)
    st.rerun()
