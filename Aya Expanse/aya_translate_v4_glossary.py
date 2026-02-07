import requests
import tiktoken
import json
import os
import re
from tqdm import tqdm
from langdetect import detect, DetectorFactory

DetectorFactory.seed = 0

def generate_translation_prompt(previous_translation, current_chunk, glossary_text):    
    return f"""
            You are a highly skilled translator specializing in Chinese-to-English translations.
            Your task is to translate the following Chinese text into accurate and fluent English, without paraphrasing in any way. 
            Translated text must be returned for all provided Chinese text without exception.
            Below is a glossary of specific terms. The English names specified in the glossary must be used as-is, if the corresponding Chinese name is found in the text.
            Do not modify these names in any way, use them exactly as they appear in the glossary, with the exact same spelling. 
            For example, if the glossary says "埃伊娜" is 'Eina', you MUST translate it as 'Eina', NOT 'Einah' or 'Ein'.
            Do not use honorifics unless they appear in the glossary.

            Glossary:
            {glossary_text}

            Here is the previous section that was translated, so that you may continue from there:
            {previous_translation}

            Now, translate the following Chinese text, continuing from where the previous section left off, without repetition of anything already covered there. 
            Your response will be directly added to the final translated content, so make sure you directly start with the translation, without saying anything before it.
            Your response must absolutely be in English - will be penalized for any Chinese characters in your response.
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

def filter_glossary_for_chunk(chunk, glossary):
    relevant_glossary = {}
    for key, values in glossary.items():
        if key in chunk:
            relevant_glossary[key] = values
    return relevant_glossary

def is_valid_translation(response):
    try:
        # Check if the dominant language is English
        language = detect(response)
        if language != "en":
            return False
        
        # Check if the text contains Chinese characters
        chinese_characters = re.search(r'[\u4e00-\u9fff]', response)
        if chinese_characters:
            return False  # Invalid if any Chinese characters are found
        
        if "translation" in response.lower():
            return False  # Invalid due to preceding text

        return True
    except Exception:
        return False

def process_file(input_file, output_file, glossary_file="glossary.json", tokens_per_chunk=1000, overlap_tokens=50, max_retries=3):
    chunks = get_chunks(input_file, tokens_per_chunk=tokens_per_chunk, overlap_tokens=overlap_tokens)
    
    # Load the glossary
    if os.path.exists(glossary_file):
        with open(glossary_file, 'r', encoding='utf-8') as gf:
            glossary = json.load(gf)
    else:
        print("Glossary file not found. Exiting.")
        return

    results = []
    previous_translation = "[No previous context available]"  # Initial value for the first chunk
    
    with tqdm(total=len(chunks), desc="Translating") as pbar:
        for chunk in chunks:
            glossary_subset = filter_glossary_for_chunk(chunk, glossary)
            glossary_text = "\n".join([f'"{key}": "{", ".join(values)}"' for key, values in glossary_subset.items()])
            retries = 0
            valid_response = False

            while retries < max_retries and not valid_response:
                prompt = generate_translation_prompt(previous_translation, chunk, glossary_text)
                response = generate_response(prompt)
                
                if is_valid_translation(response):
                    valid_response = True                    
                    results.append(response)
                    # Update previous_translation for continuity
                    previous_translation = response.strip().split('\n')[-1]
                else:
                    retries += 1
                    print(f"Retrying chunk due to invalid translation (Attempt {retries}/{max_retries})")

            if not valid_response:
                print(f"Failed to get a valid translation for chunk after {max_retries} attempts.")
                results.append("[Translation failed for this chunk]")

            pbar.update(1)

    # Write the translations to the output file
    with open(output_file, 'w', encoding='utf-8') as out_file:
        for result in results:
            out_file.write(result + "\n\n")

if __name__ == "__main__":
    input_file = "Chinese.txt"
    output_file = "English.txt"
    glossary_file = "glossary.json"

    process_file(input_file, output_file, glossary_file)
    print("Translation complete. Check English.txt for results.")
