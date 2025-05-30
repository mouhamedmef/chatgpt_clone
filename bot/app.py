from operator import itemgetter
import os
import ollama
import subprocess
import threading
import requests
import asyncio
from dotenv import load_dotenv
from typing import Dict, Optional
import chainlit as cl
from chainlit.data.sql_alchemy import SQLAlchemyDataLayer
from chainlit.types import ThreadDict

os.environ['CHAINLIT_AUTH_SECRET'] = "e@icA~%6O-aA2yQ9oo0X^XY5w4nI-^eu=kbW-lhoZA%Qs:gXWjQ=RHZPqbS0ITdn"
os.environ['DATABASE_URL'] = "postgresql+asyncpg://chainlit_user:securepassword@localhost:5000/chainlit_db"
def _ollama():
    os.environ['OLLAMA_HOST']='0.0.0.0:11434'
    os.environ['OLLAMA_ORIGINS']= '*'
    subprocess.Popen(['ollama','serve'])
def start_ollama():
    thread = threading.Thread(target=_ollama)
    thread.deamon =True
    thread.start()
@cl.password_auth_callback
def auth(username:str,password:str):
    return cl.User(identifier=username)


@cl.on_chat_start
async def on_chat_start():
    start_ollama()
    cl.user_session.set('chat_history',[])
@cl.data_layer
def get_data_layer():
    return SQLAlchemyDataLayer(conninfo=os.getenv("DATABASE_URL"))
@cl.on_chat_resume
async def on_chat_resume(thread:ThreadDict):
    start_ollama()
    cl.user_session.set("chat_history",[])
    for message in thread['steps']:
        if message['type'] == 'user_message':
            cl.user_session.get("chat_history").append({'role':'assistant','content':message['output']})

@cl.on_message
async def on_message(message:cl.message):
    chat_history = cl.user_session.get("chat_history")
    model ="qwen3:0.6b"
    chat_history.append({'role':'user','content':message.content})
    cb =cl.Message(content="")
    await cb.send()
    def generate_chunks():
        return ollama.chat(
            model=model,
            messages=chat_history,
            stream=True,
            options={'stop':['<|im_end|>']}
        )
    loop= asyncio.get_event_loop()
    stream = await loop.run_in_executor(None,generate_chunks)
    assistant_response =''
    for chunk in stream:
        content = chunk.get("message",{}).get("content","")
        if content:
            assistant_response += content
            await cb.stream_token(content)
    chat_history.append({'role':'assistant','content':assistant_response})
    await cb.update()
