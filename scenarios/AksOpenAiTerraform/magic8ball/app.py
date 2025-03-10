import os
from openai import AzureOpenAI
import streamlit as st
from azure.identity import WorkloadIdentityCredential, get_bearer_token_provider

azure_deployment = os.getenv("AZURE_OPENAI_DEPLOYMENT")
azure_endpoint = os.getenv("AZURE_OPENAI_ENDPOINT")
workload_identity_client_id = os.getenv("WORKLOAD_IDENTITY_CLIENT_ID")

client = AzureOpenAI(
    api_version="2024-10-21",
    azure_endpoint=azure_endpoint,
    azure_ad_token_provider=get_bearer_token_provider(
        WorkloadIdentityCredential(client_id=workload_identity_client_id),
        "https://cognitiveservices.azure.com/.default",
    ),
)


def ask_openai_api(messages: list[str]):
    completion = client.chat.completions.create(
        messages=messages, model=azure_deployment, stream=True, max_tokens=20
    )
    return completion


assistant_prompt = """
Answer as a magic 8 ball and make random predictions.
If the question is not clear, respond with "Ask the Magic 8 Ball a question about your future."
"""

# Init state
if "messages" not in st.session_state:
    st.session_state.messages = [{"role": "system", "content": assistant_prompt}]
if "disabled" not in st.session_state:
    st.session_state.disabled = False

st.title(":robot_face: Magic 8 Ball")
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

    # Print Response
    with st.chat_message("assistant"):
        messages = st.session_state.messages
        with st.spinner("Loading..."):
            response = st.write_stream(ask_openai_api(messages))
    st.session_state.messages.append({"role": "assistant", "content": response})

    # Re-enable textbox
    st.session_state.disabled = False
    st.rerun()
