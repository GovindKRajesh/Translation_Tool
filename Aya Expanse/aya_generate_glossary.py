import tiktoken
import json
from tqdm import tqdm
import os
import ollama
import re

system_message = """
        You are a highly skilled translator specializing in Chinese-to-English translations.
        Your task is to list out the names of all characters, organizations, places and skills/magic spells that are found in the provided text, along with their English translations, in JSON format.
        For example, your output should look like this:
        {{
            "蜜西亚": "Misha",
            "赫斯缇雅眷族": "Hestia Familia",
            "埃伊娜": "Eina"
        }}
        There is no need for any nesting in the JSON structure.
        If you find any text within '【】' type brackets, they must be extracted.
        If there are no names in the text, you may return an empty JSON object.
        """

def generate_prompt(current_chunk):
    return f"""
        Here is the Chinese text that you must extract names from:
        {current_chunk}
        """

def get_chunks(file_path, tokens_per_chunk=1000, encoding_name="cl100k_base"):
    tokenizer = tiktoken.get_encoding(encoding_name)

    with open(file_path, 'r', encoding='utf-8') as file:
        lines = file.readlines()

    chunks = []
    current_chunk = []
    current_tokens = 0

    for line in lines:
        line_tokens = tokenizer.encode(line)
        line_token_count = len(line_tokens)

        # Check if adding the current line would exceed the token limit
        if current_tokens + line_token_count > tokens_per_chunk:
            # Finalize the current chunk
            chunks.append(tokenizer.decode(sum(current_chunk, [])))
            current_chunk = []
            current_tokens = 0

        # Add the current line to the chunk
        current_chunk.append(line_tokens)
        current_tokens += line_token_count

    # Add any remaining lines as the last chunk
    if current_chunk:
        chunks.append(tokenizer.decode(sum(current_chunk, [])))

    total_tokens = sum(len(tokenizer.encode(chunk)) for chunk in chunks)
    print(f"Total number of tokens in the original file: {total_tokens}")
    print(f"Number of chunks created: {len(chunks)}")

    return chunks

def generate_response(prompt, model="aya-expanse"):
    messages = [
            {"role": "system", "content": system_message},
            {"role": "user", "content": prompt}
            ]
    response = ollama.chat(model, messages)
    return response["message"]["content"].strip()

def extract_json_from_response(response):
    """
    Extracts JSON object from the model's response, ignoring any extraneous text.
    Looks for the JSON enclosed within ```json blocks or standalone JSON.
    """
    match = re.search(r"```json\s*(\{.*?\})\s*```", response, re.DOTALL)
    if not match:
        match = re.search(r"(\{.*?\})", response, re.DOTALL)
    if match:
        try:
            return json.loads(match.group(1))
        except json.JSONDecodeError:
            return None
    return None

def update_glossary(new_data, glossary):
    chinese_regex = re.compile(r'[\u4e00-\u9fff]')
    english_regex = re.compile(r'^[a-zA-Z0-9\s.,\'"()\-]+$')
    for key, value in new_data.items():
        try:
            if value and not isinstance(value, str):
                if isinstance(value, list):
                    if isinstance(value[0], str):
                        value = value[0]
                    else:
                        print(f"\nIgnored -> Key: {key}, Value: {value} (Not a string)")
                        continue
                else:
                    print(f"\nIgnored -> Key: {key}, Value: {value} (Not a string)")
                    continue
            if chinese_regex.search(key) and english_regex.match(value):
                if key not in glossary:
                    glossary[key] = [value]
                    print(f"\nAdded to Glossary -> Chinese: {key}, Value: {value}")
            else:
                print(f"\nIgnored -> Key: {key} (Must be Chinese), Value: {value} (Must be English)")
        except Exception:
            print(f"\nIgnored -> Key: {key}, Value: {value} - Error in data type")
            continue

def process_file(input_file, glossary_file="glossary.json", tokens_per_chunk=1000):
    chunks = get_chunks(input_file, tokens_per_chunk=tokens_per_chunk)
    
    # Load existing glossary or initialize an empty one
    if os.path.exists(glossary_file):
        with open(glossary_file, 'r', encoding='utf-8') as gf:
            glossary = json.load(gf)
    else:
        glossary = {}

    with tqdm(total=len(chunks), desc="Processing") as pbar:
        for chunk in chunks:
            prompt = generate_prompt(chunk)
            response = generate_response(prompt)
            
            new_data = extract_json_from_response(response)
            if new_data:  # Only update if valid JSON is found
                update_glossary(new_data, glossary)

            pbar.update(1)

            # Periodically save glossary
            with open(glossary_file, 'w', encoding='utf-8') as gf:
                json.dump(glossary, gf, ensure_ascii=False, indent=4)

if __name__ == "__main__":
    input_file = "Chinese.txt"
    glossary_file = "glossary.json"

    process_file(input_file, glossary_file)
    print("Processing complete. Check glossary.json for the extracted terms.")
