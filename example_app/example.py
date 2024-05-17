import requests
import boto3
from langchain.prompts import PromptTemplate

def setup_s3(bucket_name: str):
    """
    Creates an S3 client and uploads a file to the specified bucket.
    """
    s3 = boto3.client('s3')
    response = s3.upload_file('t8.shakespeare.txt', bucket_name, 't8.shakespeare.txt')

def provision_resources(api_url: str, llm_name: str, embed_name: str, vdb_name: str):
    """
    Provisions resources (LLM, Embedding model, and Vector Database) via API calls.
    """
    response = requests.post(f"{api_url}/model/create", json={"name": llm_name, "model": "mistral-7b"})
    response = requests.post(f"{api_url}/model/create", json={"name": embed_name, "model": "gte-large"})
    response = requests.post(f"{api_url}/vdb/create", json={"name": vdb_name})

def status_check(api_url: str, llm_name: str, embed_name: str, vdb_name: str):
    """
    Checks the status of provisioned resources via API calls.
    """
    response = requests.post(f"{api_url}/model/status", json={"name": llm_name})
    response = requests.post(f"{api_url}/model/status", json={"name": embed_name})
    response = requests.post(f"{api_url}/vdb/status", json={"name": vdb_name})

def setup_embeddings(api_url, embed_name, src_bucket, target_bucket, vdb_name):
    """
    Embeds documents in the source bucket and adds them to the Vector Database via API calls.
    """
    response = requests.post(f"{api_url}/vdb/embed", json={"model": embed_name, "src": src_bucket, "target": target_bucket, "vdb": vdb_name})
    response = requests.post(f"{api_url}/vdb/add", json={"name": vdb_name, "src": target_bucket})

def start_chat(api_url, model_name, embed_name, vdb_name, query):
    """
    Starts a new chat session with the LLM, retrieving relevant documents from the Vector Database
    and creating a chat history.
    """
    response = requests.post(f"{api_url}/vdb/query", json={"model": embed_name, "query": query, "name": vdb_name})
    vdb_data = response['data']
    response = requests.post(f"{api_url}/model/query", json={"model": model_name, "query": query})
    answer = response.json()["response"]
    response = requests.post(f"{api_url}/history/new", json={"q": query, "a": answer})
    chat_id = response.json()["chat_id"]
    return answer, chat_id

def continue_chat(api_url, model_name, embed_name, vdb_name, query, chat_id):
    """
    Continues an existing chat session with the LLM, retrieving relevant documents from the Vector Database
    and appending to the chat history.
    """
    response = requests.post(f"{api_url}/history/get", json={"chat_id": chat_id})
    chat_data = response.json()
    response = requests.post(f"{api_url}/vdb/query", json={"model": embed_name, "query": query, "name": vdb_name})
    vdb_data = response['data']
    response = requests.post(f"{api_url}/model/query", json={"model": model_name, "query": query})
    answer = response.json()["response"]
    response = requests.post(f"{api_url}/history/append", json={"q": query, "a": answer, "chat_id": chat_id})
    return answer

def teardown_resources(api_url: str, llm_name: str, embed_name: str, vdb_name: str):
    """
    Tears down provisioned resources via API calls.
    """
    response = requests.post(f"{api_url}/model/delete", json={"name": llm_name})
    response = requests.post(f"{api_url}/model/delete", json={"name": embed_name})
    response = requests.post(f"{api_url}/vdb/delete", json={"name": vdb_name})

def build_query(query, data, history=None):
    """
    Builds a prompt for the LLM using the provided query, data, and optional chat history.
    """
    system_message = "You are a helpful AI assistant."
    human_message = f"Human: {query}"
    data_prefix = "\n".join([f"DATA: {d}" for d in data])
    dialogue_history = ""
    if history:
        dialogue_history = "\n".join([f"Human: {h[0]}\nAI: {h[1]}" for h in history])
    prompt_template = PromptTemplate(
        input_variables=["system", "data", "history", "human"],
        template="{system}\n{data}\n{history}\n{human}",
    )
    prompt = prompt_template.format(
        system=system_message,
        data=data_prefix,
        history=dialogue_history,
        human=human_message,
    )
    return prompt

def main():
    api_url = "https://api.example.com"
    llm_name = "llm"
    embed_name = "embed"
    vdb_name = "vdb"
    src_bucket = "src_bucket"
    target_bucket = "target_bucket"
    query1 = "What is the capital of France?"
    query2 = "And what is the tallest building in that city?"
    chat_id = None

    setup_s3(src_bucket)
    provision_resources(api_url, llm_name, embed_name, vdb_name)
    status_check(api_url, llm_name, embed_name, vdb_name)
    setup_embeddings(api_url, embed_name, src_bucket, target_bucket, vdb_name)
    answer, chat_id = start_chat(api_url, llm_name, embed_name, vdb_name, query1)
    print(answer)
    answer = continue_chat(api_url, llm_name, embed_name, vdb_name, query2, chat_id)
    print(answer)
    teardown_resources(api_url, llm_name, embed_name, vdb_name)

if __name__ == "__main__":
    main()