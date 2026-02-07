import requests
import tiktoken
import json
from tqdm import tqdm

def generate_prompt(previous_translation, current_chunk):
    return f"""
        You are a highly skilled translator specializing in Chinese-to-English translations.
        Your task is to translate the following Chinese text into accurate and fluent English.
        The previous translated English context is provided to ensure continuity:
            
        Previous Translation:
        {previous_translation}

        Now, translate the following Chinese text, continuing from where the previous section left off, without repetition:
        {current_chunk}
        """

def get_chunks(file_path, tokens_per_chunk=1000, overlap_tokens=50, encoding_name="cl100k_base"):
    tokenizer = tiktoken.get_encoding(encoding_name)
    
    with open(file_path, 'r', encoding='utf-8') as file:
        text = file.read()
    
    tokens = tokenizer.encode(text)
    total_tokens = len(tokens)
    print(f"Total number of tokens in the original file: {total_tokens}")
    
    chunks = []
    for i in range(0, len(tokens), tokens_per_chunk - overlap_tokens):
        chunk = tokens[i:i + tokens_per_chunk]
        chunks.append(tokenizer.decode(chunk))
    
    return chunks

def generate_response(prompt, model="aya-expanse", url="http://localhost:11434/api/generate"):
    headers = {"Content-Type": "application/json"}
    payload = {
        "model": model,
        "prompt": prompt,
        "stream": False
    }

    response = requests.post(url, headers=headers, data=json.dumps(payload))
    if response.status_code == 200:
        result = response.json()
        return result.get("response", "No response field found in the API response.")
    else:
        return f"Error: {response.status_code}"

def process_file(input_file, output_file, tokens_per_chunk=1000, overlap_tokens=50):
    chunks = get_chunks(input_file, tokens_per_chunk=tokens_per_chunk, overlap_tokens=overlap_tokens)
    
    results = []
    previous_translation = "[No previous context available]"  # Initial value for the first chunk
    
    with tqdm(total=len(chunks), desc="Translating") as pbar:
        for chunk in chunks:
            prompt = generate_prompt(previous_translation, chunk)
            response = generate_response(prompt)
            results.append(response)
            pbar.update(1)

            # Update previous_translation to maintain context
            previous_translation = response.strip().split('\n')[-1]  # Use last line for continuity

    # Write results to the output file in the correct order
    with open(output_file, 'w', encoding='utf-8') as out_file:
        for result in results:
            out_file.write(result + "\n\n")

if __name__ == "__main__":
    input_file = "Chinese.txt"
    output_file = "English.txt"

    process_file(input_file, output_file)
    print("Translation complete. Check English.txt for results.")
