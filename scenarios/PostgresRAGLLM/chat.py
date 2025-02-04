import argparse
import logging
from textwrap import dedent

from langchain_text_splitters import RecursiveCharacterTextSplitter
from openai import AzureOpenAI

from db import VectorDatabase

# Configure logging
logging.basicConfig(level=logging.DEBUG)

parser = argparse.ArgumentParser()
parser.add_argument('--api-key', dest='api_key', type=str)
parser.add_argument('--endpoint', dest='endpoint', type=str)
parser.add_argument('--pguser', dest='pguser', type=str)
parser.add_argument('--phhost', dest='phhost', type=str)
parser.add_argument('--pgpassword', dest='pgpassword', type=str)
parser.add_argument('--pgdatabase', dest='pgdatabase', type=str)
parser.add_argument('--populate', dest='populate', action="store_true")
parser.add_argument('--question', dest='question', type=str, help="Question to ask the chatbot")
args = parser.parse_args()


class ChatBot:
    def __init__(self):
        logging.debug("Initializing ChatBot")
        self.db = VectorDatabase(pguser=args.pguser, pghost=args.phhost, pgpassword=args.pgpassword, pgdatabase=args.pgdatabase)
        self.api = AzureOpenAI(
            azure_endpoint=args.endpoint,
            api_key=args.api_key,
            api_version="2024-06-01",
        )
        self.text_splitter = RecursiveCharacterTextSplitter(
            chunk_size=512,
            chunk_overlap=20,
            length_function=len,
            is_separator_regex=False,
        )

    def load_file(self, text_file: str):
        logging.debug(f"Loading file: {text_file}")
        with open(text_file, encoding="UTF-8") as f:
            data = f.read()
            chunks = self.text_splitter.create_documents([data])
            for i, chunk in enumerate(chunks):
                text = chunk.page_content
                embedding = self.__create_embedding(text)
                self.db.save_embedding(i, text, embedding)

    def __create_embedding(self, text: str):
        logging.debug(f"Creating embedding for text: {text[:30]}...")
        return self.api.embeddings.create(model="text-embedding-ada-002", input=text).data[0].embedding

    def get_answer(self, question: str):
        logging.debug(f"Getting answer for question: {question}")
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

    if args.populate:
        logging.debug("Loading embedding data into database...")
        chat_bot.load_file("knowledge.txt")
        logging.debug("Done loading data.")
        return

    if args.question:
        logging.debug(f"Question provided: {args.question}")
        print(chat_bot.get_answer(args.question))
        return

    while True:
        q = input("Ask a question (q to exit): ")
        if q == "q":
            break
        print(chat_bot.get_answer(q))


if __name__ == "__main__":
    main()