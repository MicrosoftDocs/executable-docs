# https://levelup.gitconnected.com/its-time-to-create-a-private-chatgpt-for-yourself-today-6503649e7bb6
#
# Make sure to provide a value for the following environment variables:
#  - AZURE_OPENAI_BASE (ex: https://eastus.api.cognitive.microsoft.com/)
#  - AZURE_OPENAI_DEPLOYMENT
#  - AZURE_OPENAI_MODEL
#  - AZURE_OPENAI_VERSION

import os
import time
import openai
import logging
import streamlit as st
from streamlit_chat import message
from azure.identity import DefaultAzureCredential

# Environment Variables
api_version = os.environ.get("AZURE_OPENAI_VERSION")
engine = os.getenv("AZURE_OPENAI_DEPLOYMENT")
model = os.getenv("AZURE_OPENAI_MODEL")

title = "Magic 8 Ball"
text_input_label = "Pose your question and cross your fingers!"
image_file_name = "magic8ball.png"
image_width = 80
temperature = 0.9
system = """
You are the infamous Magic 8 Ball. You need to randomly reply to any question with one of the following answers:

- It is certain.
- It is decidedly so.
- Without a doubt.
- Yes definitely.
- You may rely on it.
- As I see it, yes.
- Most likely.
- Outlook good.
- Yes.
- Signs point to yes.
- Reply hazy, try again.
- Ask again later.
- Better not tell you now.
- Cannot predict now.
- Concentrate and ask again.
- Don't count on it.
- My reply is no.
- My sources say no.
- Outlook not so good.
- Very doubtful.

Add a short comment in a pirate style at the end! Follow your heart and be creative! 
For mor information, see https://en.wikipedia.org/wiki/Magic_8_Ball
"""

# Authenticate to Azure OpenAI
default_credential = DefaultAzureCredential()
openai_token = default_credential.get_token("https://cognitiveservices.azure.com/.default")

# Init session_state
if 'prompts' not in st.session_state:
  st.session_state['prompts'] = [{"role": "system", "content": system}]
if 'generated' not in st.session_state:
  st.session_state['generated'] = []
if 'past' not in st.session_state:
  st.session_state['past'] = []


def on_submit():
  # Avoid handling the event twice when clicking the Send button
  chat_input = st.session_state['user']
  st.session_state['user'] = ""
  if (chat_input == '' or
      (len(st.session_state['past']) > 0 and chat_input == st.session_state['past'][-1])):
    return
  
  # Save history
  st.session_state['past'].append(chat_input)

  # Refresh token every 45 min
  if st.session_state.get('openai_token') and st.session_state['openai_token'].expires_on < int(time.time()) - 45 * 60:
    st.session_state['openai_token'] = default_credential.get_token("https://cognitiveservices.azure.com/.default")
    openai.api_key = st.session_state['openai_token'].token

  # Generate API response
  st.session_state['prompts'].append({"role": "user", "content": chat_input})
  completion = openai.ChatCompletion.create(
    engine = engine,
    model = model,
    messages = st.session_state['prompts'],
    temperature = temperature,
  )
  message = completion.choices[0].message.content
  st.session_state['generated'].append(message)
  st.session_state['prompts'].append({"role": "assistant", "content": message})


def reset():
  st.session_state['prompts'] = [{"role": "system", "content": system}]
  st.session_state['past'] = []
  st.session_state['generated'] = []
  st.session_state['user'] = ""


# Row 1
col1, col2 = st.columns([1, 7])
with col1:  # Robot icon
  st.image(image = os.path.join("icons", image_file_name), width = image_width)
with col2:  # Title
  st.title(title)

# Row 2
col3, col4, col5 = st.columns([7, 1, 1])
with col3:  # Text box
  user_input = st.text_input(text_input_label, key = "user", on_change = on_submit)
with col4:  # 'Send' Button
  st.button(label = "Send")
with col5:  # 'New' Button
  st.button(label = "New", on_click = reset)

if st.session_state['generated']:
  for i in range(len(st.session_state['generated']) - 1, -1, -1):
    message(st.session_state['past'][i], is_user = True, key = str(i) + '_user', avatar_style = "fun-emoji", seed = "Nala")
    message(st.session_state['generated'][i], key = str(i), avatar_style = "bottts", seed = "Fluffy")


# Customize Streamlit UI using CSS
st.markdown("""
<style>

div.stButton > button:first-child {
    background-color: #eb5424;
    color: white;
    font-size: 20px;
    font-weight: bold;
    border-radius: 0.5rem;
    padding: 0.5rem 1rem;
    border: none;
    box-shadow: 0 0.5rem 1rem rgba(0,0,0,0.15);
    width: 300 px;
    height: 42px;
    transition: all 0.2s ease-in-out;
} 

div.stButton > button:first-child:hover {
    transform: translateY(-3px);
    box-shadow: 0 1rem 2rem rgba(0,0,0,0.15);
}

div.stButton > button:first-child:active {
    transform: translateY(-1px);
    box-shadow: 0 0.5rem 1rem rgba(0,0,0,0.15);
}

div.stButton > button:focus:not(:focus-visible) {
    color: #FFFFFF;
}

@media only screen and (min-width: 768px) {
  /* For desktop: */
  div {
      font-family: 'Roboto', sans-serif;
  }

  div.stButton > button:first-child {
      background-color: #eb5424;
      color: white;
      font-size: 20px;
      font-weight: bold;
      border-radius: 0.5rem;
      padding: 0.5rem 1rem;
      border: none;
      box-shadow: 0 0.5rem 1rem rgba(0,0,0,0.15);
      width: 300 px;
      height: 42px;
      transition: all 0.2s ease-in-out;
      position: relative;
      bottom: -32px;
      right: 0px;
  } 

  div.stButton > button:first-child:hover {
      transform: translateY(-3px);
      box-shadow: 0 1rem 2rem rgba(0,0,0,0.15);
  }

  div.stButton > button:first-child:active {
      transform: translateY(-1px);
      box-shadow: 0 0.5rem 1rem rgba(0,0,0,0.15);
  }

  div.stButton > button:focus:not(:focus-visible) {
      color: #FFFFFF;
  }

  input {
      border-radius: 0.5rem;
      padding: 0.5rem 1rem;
      border: none;
      box-shadow: 0 0.5rem 1rem rgba(0,0,0,0.15);
      transition: all 0.2s ease-in-out;
      height: 40px;
  }
}
</style>
""")