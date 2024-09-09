import os
import sys
from textwrap import dedent

from langchain_text_splitters import RecursiveCharacterTextSplitter
from openai import AzureOpenAI

from db import VectorDatabase

API_KEY = os.environ["API_KEY"]
ENDPOINT = os.environ["ENDPOINT"]


class ChatBot:
    def __init__(self):
        self.db = VectorDatabase()
        self.api = AzureOpenAI(
            azure_endpoint=ENDPOINT,
            api_key=API_KEY,
            api_version="2024-02-01",
        )
        self.text_splitter = RecursiveCharacterTextSplitter(
            chunk_size=512,
            chunk_overlap=20,
            length_function=len,
            is_separator_regex=False,
        )

    def load_file(self, text_file: str):
        with open(text_file, encoding="UTF-8") as f:
            data = f.read()
            chunks = self.text_splitter.create_documents([data])
            for i, chunk in enumerate(chunks):
                text = chunk.page_content
                embedding = self.__create_embedding(text)
                self.db.save_embedding(i, text, embedding)

    def __create_embedding(self, text: str):
        return self.api.embeddings.create(model="text-embedding-ada-002", input=text).data[0].embedding

    def get_answer(self, question: str):
        question_embedding = self.__create_embedding(question)
        context = self.db.search_documents(question_embedding)

        # fmt: off
        system_promt = dedent(f"""\
        You are a friendly and helpful AI assistant. I am going to ask you a question about Zytonium. 
        Use the following piece of context to answer the question.
        If the context is empty, try your best to answer without it.
        Never mention the context.
        Try to keep your answers concise unless asked to provide details.

        Context: {context}

        That is the end of the context.
        """)
        # fmt: on

        response = self.api.chat.completions.create(
            model="gpt-4",
            messages=[
                {"role": "system", "content": system_promt},
                {"role": "user", "content": question},
            ],
        )
        return response.choices[0].message.content


def main():
    chat_bot = ChatBot()

    if sys.argv[1] == "--populate":
        print("Loading embedding data into database...")
        chat_bot.load_file("knowledge.txt")
        print("Done loading data.")

    while True:
        q = input("Ask a question (q to exit): ")
        if q == "q":
            break
        print(chat_bot.get_answer(q))


if __name__ == "__main__":
    main()
