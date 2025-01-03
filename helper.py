from groq import Groq
from langchain_community.embeddings import HuggingFaceEmbeddings
from dotenv import load_dotenv
import os

load_dotenv()

client = Groq(api_key=os.getenv("GROQ_API"))


def generate(prompt):
    print("Generating response...")
    chat_completion = client.chat.completions.create(
        messages=[
            {
                "role": "user",
                "content": prompt,
            }
        ],
        model="llama3-70b-8192",
    )
    return chat_completion.choices[0].message.content


def gen_embed(text):
    model = HuggingFaceEmbeddings(
            model_name="sentence-transformers/all-mpnet-base-v2"
        )
    return model.embed_query(text)


if __name__ == "__main__":
    while True:
        user_input = input("You: ")
        response = generate(user_input)
        print(f"AI Agent: {response}")
