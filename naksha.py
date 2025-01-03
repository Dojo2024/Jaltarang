from groq import Groq
from langchain_community.embeddings import HuggingFaceEmbeddings
from langchain.prompts import PromptTemplate
import sqlite3
import numpy as np
import json
from dotenv import load_dotenv
import os

load_dotenv()

class SQLiteRAGSystem:
    def __init__(self, groq_api_key, db_path):
        """
        Initialize RAG system with Groq API key and SQLite database path
        """
        self.client = Groq(api_key=groq_api_key)
        self.db_path = db_path
        
        
        self.embeddings = HuggingFaceEmbeddings(
            model_name="sentence-transformers/all-mpnet-base-v2"
        )
        
        
        self.prompt_template = PromptTemplate(
            template="""
            You are a data analyst working for a naval intelligence agency. You have been tasked with analyzing a series of reports related to maritime activities. Your job is to provide detailed insights and answers to specific questions based on the information provided in the reports.
            Use the following pieces of context to answer the question at the end.
            Follow the guidelines below:
            1. Read the context carefully to understand the information provided.
            2. Analyze the data to identify key points and relevant details.
            3. Use your analytical skills to derive insights and provide accurate answers.
            4. Be concise and clear in your responses.
            5. Provide structured answers with bullet points where necessary.
            6. The answers should be based on the information provided in the context and your analytical reasoning.
            7. You should not introduce new information that is not present in the context.
            8. Properly structure your response with new lines and bullet points for clarity.
            The answer should contain the following:
            1. A clear, structured response to the question, highlighting only key information in concise bulleted manner.
            2. A short summary of the structured response in a single paragraph.
            If you don't know the answer, just say that you don't know, don't try to make up an answer.
            Start your response with "Answer:".
            
            Context: {context}
            
            Question: {question}
            
            """,
            input_variables=["context", "question"]
        )

    def _cosine_similarity(self, embedding1, embedding2):
        """Calculate cosine similarity between two embeddings"""
        return np.dot(embedding1, embedding2) / (np.linalg.norm(embedding1) * np.linalg.norm(embedding2))

    def query(self, question, num_docs=3):
        """
        Query the RAG system using the SQLite database
        """
        try:
            
            question_embedding = self.embeddings.embed_query(question)
            
            
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                cursor.execute("SELECT summary, structure, embedding FROM RAG_data")
                results = cursor.fetchall()
            
            
            similarities = []
            for summary, structure, embedding_json in results:
                embedding = np.array(json.loads(embedding_json))
                similarity = self._cosine_similarity(question_embedding, embedding)
                similarities.append((similarity, summary, structure))
            
            
            similarities.sort(reverse=True)
            top_docs = similarities[:num_docs]
            
            
            context = "\n\n".join([doc[1]+doc[2] for doc in top_docs])
            
            
            prompt = self.prompt_template.format(
                context=context,
                question=question
            )
            
            
            chat_completion = self.client.chat.completions.create(
                messages=[
                    {
                        "role": "user",
                        "content": prompt,
                    }
                ],
                model="llama3-70b-8192",
            )
            
            return chat_completion.choices[0].message.content
            
        except sqlite3.Error as e:
            return f"Database error: {str(e)}"
        except Exception as e:
            return f"Error processing query: {str(e)}"

def main():
    rag = SQLiteRAGSystem(
        groq_api_key=os.getenv("GROQ_API"),
        db_path="data_classification.db"
    )
    
    while True:
        question = input("\nEnter your question (or 'quit' to exit): ")
        if question.lower() == 'quit':
            break
        
        answer = rag.query(question)
        print(f"\nAnswer: {answer}")


def chat_with_agent(user_input):
    rag = SQLiteRAGSystem(
        groq_api_key=os.getenv("GROQ_API"),
        db_path="data_classification.db"
    )
    return rag.query(user_input).replace("Answer:", "").strip()

if __name__ == "__main__":
    main()