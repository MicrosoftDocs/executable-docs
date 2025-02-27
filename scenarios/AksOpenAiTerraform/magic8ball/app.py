# https://levelup.gitconnected.com/its-time-to-create-a-private-chatgpt-for-yourself-today-6503649e7bb6

import os
from openai import AzureOpenAI
import streamlit as st
from azure.identity import DefaultAzureCredential, get_bearer_token_provider

deployment = os.getenv("AZURE_OPENAI_DEPLOYMENT")
azure_endpoint = os.getenv("AZURE_OPENAI_ENDPOINT")

client = AzureOpenAI(
    api_version="2024-10-21",
    azure_endpoint=azure_endpoint,
    azure_ad_token_provider=get_bearer_token_provider(
        DefaultAzureCredential(), "https://cognitiveservices.azure.com/.default"
    ),
)


def call_api(messages):
    completion = client.chat.completions.create(
        model=deployment,
        messages=messages,
    )
    return completion.choices[0].message.content


assistant_prompt = """
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

# Init state
if "messages" not in st.session_state:
    st.session_state.messages = [{"role": "system", "content": assistant_prompt}]
if "disabled" not in st.session_state:
    st.session_state.disabled = False

st.title("Magic 8 Ball")
for message in st.session_state.messages[1:]:  # Print previous messages
    with st.chat_message(message["role"]):
        st.markdown(message["content"])


def disable_chat():
    st.session_state.disabled = True


if prompt := st.chat_input(
    "Ask your question", on_submit=disable_chat, disabled=st.session_state.disabled
):
    # Print Question
    st.session_state.messages.append({"role": "user", "content": prompt})
    with st.chat_message("user"):
        st.write(prompt)

    # Loading indicator
    response = None
    with st.spinner("Loading response..."): 
        response = call_api(st.session_state.messages)

    # Print Response
    st.session_state.messages.append({"role": "assistant", "content": response})
    with st.chat_message("assistant"):
        st.write(response)

    # Re-enable textbox
    st.session_state.disabled = False
    st.rerun()
