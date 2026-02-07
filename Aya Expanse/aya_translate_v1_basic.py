import requests
import json
import tiktoken

def get_chunks(file_path, tokens_per_chunk=1000, encoding_name="cl100k_base"):
    # Use a compatible tokenizer for tokenization
    tokenizer = tiktoken.get_encoding(encoding_name)
    
    with open(file_path, 'r', encoding='utf-8') as file:
        text = file.read()
    
    tokens = tokenizer.encode(text)
    
    for i in range(0, len(tokens), tokens_per_chunk):
        yield tokenizer.decode(tokens[i:i + tokens_per_chunk])

def generate_response(prompt, model="aya-expanse", url="http://localhost:11434/api/generate"):
    headers = {"Content-Type": "application/json"}
    payload = {
        "model": model,
        "prompt": "Translate the following to English: " + prompt,
        "stream": False
    }

    try:
        response = requests.post(url, headers=headers, data=json.dumps(payload))
        response.raise_for_status()
        result = response.json()
        return result.get("response", "No response field found in the API response.")
    except requests.exceptions.RequestException as e:
        return f"An error occurred: {e}"
    except json.JSONDecodeError:
        return "Failed to decode JSON response from the API."

def process_file(input_file, output_file):
    with open(output_file, 'w', encoding='utf-8') as out_file:
        for chunk in get_chunks(input_file):
            response = generate_response(chunk)
            out_file.write(response + "\n\n")  # Write translated chunk

if __name__ == "__main__":
    input_file = "Chinese.txt"
    output_file = "English.txt"
    
    process_file(input_file, output_file)
    print("Translation complete. Check English.txt for results.")
