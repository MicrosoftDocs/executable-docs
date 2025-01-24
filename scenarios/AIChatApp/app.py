import os
from langchain.document_loaders import TextLoader
from langchain.indexes import VectorstoreIndexCreator
from langchain.chains import ConversationalRetrievalChain
from langchain.embeddings import OpenAIEmbeddings
from langchain.llms import OpenAI
import chainlit as cl

# Set Azure OpenAI API credentials
os.environ["OPENAI_API_TYPE"] = "azure"
os.environ["OPENAI_API_KEY"] = os.getenv("OPENAI_API_KEY")
os.environ["OPENAI_API_BASE"] = os.getenv("OPENAI_API_BASE")
os.environ["OPENAI_API_VERSION"] = "2023-03-15-preview"

# Load documents
loader = TextLoader('documents.txt')
documents = loader.load()

# Create index
index = VectorstoreIndexCreator().from_loaders([loader])

# Create conversational retrieval chain
retriever = index.vectorstore.as_retriever()
qa_chain = ConversationalRetrievalChain.from_llm(
    llm=OpenAI(temperature=0),
    retriever=retriever
)

# Initialize conversation history
history = []

@cl.on_message
async def main(message):
    global history
    result = qa_chain({"question": message, "chat_history": history})
    history.append((message, result['answer']))
    await cl.Message(content=result['answer']).send()