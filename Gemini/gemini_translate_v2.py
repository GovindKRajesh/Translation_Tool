import tiktoken
import json
import os
import re
from tqdm import tqdm
import logging
import google.generativeai as genai
from dotenv import load_dotenv

load_dotenv()
gemini_key = os.environ["GEMINI_KEY"]

# Configuring Logging
logging.basicConfig(
    filename='translation_log.log',
    level=logging.INFO,
    format='%(asctime)s - %(message)s',
    datefmt='%Y-%m-%d %H:%M:%S'
)

system_message = """
            Your role:
            You are a highly skilled translator specializing in Chinese-to-English translations.
            Your task is to translate the provided Chinese text into accurate and fluent English, without paraphrasing in any way.
            The provided text will be from the Japanese Light Novel Danmachi, so use your knowledge of the series to assist with any roadblocks in translation.
            Try to keep the translation as literal as you can, rephrasing only when it is hard to understand otherwise.

            Glossary:
            You will be provided with a glossary of specific terms. The English names specified in the glossary must be used as-is, if the corresponding Chinese name is found in the text.
            Do not modify names from the glossary in any way, use them exactly as they appear in the glossary, with the exact same spelling. Respecting the Glossary is a must.
            For example, if the glossary says "埃伊娜" is 'Eina', you MUST translate it as 'Eina', NOT 'Einah'/'Ein'/'Einar'.
            The glossary provided will only have words or phrases that exist in the provided Chinese text. Hence, all of them absolutely MUST be used in your translation. 
            You will be penalized if you do not use any word from the provided glossary.
            Do not use honorifics unless they appear in the glossary.

            Regarding your response:
            Translated text must be returned for all provided Chinese text without exception.
            Your translation must continue from where the previous section left off, without any repetition or overlap. 
            Your response will be directly added to the final translated content, so make sure you directly start with the translation, without saying anything before it.
            Your response must absolutely be in English - will be penalized for any Chinese characters in your response.
            """

failure = {
    "Incomplete": "Your previous attempt failed because you provided an incomplete translation - Chinese text was found within the output. This time, ensure that your output is entirely in English.",
    "Preceding": "Your previous attempt failed because you provided preceding text within the output. This time, make sure to directly start outputing the translation without giving any text before it.",
    "Glossary": "Your previous attempt failed because your response missed out words or phrases specified in the glossary. This time, you must ensure that all provided terms from the glossary must be used."
}

def generate_translation_prompt(previous_translation, current_chunk, glossary_text):    
    return f"""
            Glossary:
            {glossary_text}

            Here is the previous section that was translated, so that you may continue from there:
            {previous_translation}

            Now, translate the following Chinese text:
            {current_chunk}
            """

def get_chunks(file_path, tokens_per_chunk, encoding_name="cl100k_base"):
    tokenizer = tiktoken.get_encoding(encoding_name)
    with open(file_path, 'r', encoding='utf-8') as file:
        lines = file.readlines()

    chunks = []
    current_chunk = []
    current_tokens = 0

    for line in lines:
        line_tokens = tokenizer.encode(line)
        line_token_count = len(line_tokens)
        if current_tokens + line_token_count > tokens_per_chunk:
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

def generate_response(prompt, model):
    genai.configure(api_key=gemini_key)
    model = genai.GenerativeModel(model_name=model, system_instruction=system_message)
    response = model.generate_content(prompt)
    if hasattr(response, "candidates"):
        if hasattr(response.candidates[0].content, "parts"):
            return response.candidates[0].content.parts[0].text
    return prompt

def filter_glossary_for_chunk(chunk, glossary):
    relevant_glossary = {}
    for key, values in glossary.items():
        if key in chunk:
            relevant_glossary[key] = values
    return relevant_glossary

def translation_validity(response, glossary):
    try:
        # Check if the text contains Chinese characters
        chinese_characters = re.search(r'[\u4e00-\u9fff]', response)
        if chinese_characters:
            return "Incomplete"
        
        # Check for the word 'translation' to detect preceding explanatory text
        if "translation" in response.lower():
            return "Preceding"
        
        # Check glossary consistency
        for term, translations in glossary.items():
            if not any(re.search(re.escape(translation), response, re.IGNORECASE) for translation in translations):
                return "Glossary"
            
        return "AllGood"
    except Exception as e:
        print(f"Error when checking validity: {e}")
        return "Error"

def extract_english_sections(mapping_file, output_file):
    try:
        # Read the mapping.json file
        with open(mapping_file, 'r', encoding='utf-8') as f:
            mapping_data = json.load(f)
        
        # Open the output file for appending
        with open(output_file, 'a', encoding='utf-8') as out:
            for chunk_key, chunk_content in mapping_data.items():
                english_text = chunk_content.get("English", "")
                if english_text:  # Only write if English text exists
                    out.write(english_text + '\n')
        
        print(f"Extracted English sections have been appended to {output_file}.")
    except Exception as e:
        print(f"An error occurred: {e}")

def process_file(input_file, glossary_file, staging_file, output_file, tokens_per_chunk, max_retries, model="gemini-2.0-flash-thinking-exp-01-21"):
    chunks = get_chunks(input_file, tokens_per_chunk=tokens_per_chunk)

    # Load the glossary
    if os.path.exists(glossary_file):
        with open(glossary_file, 'r', encoding='utf-8') as gf:
            glossary = json.load(gf)
    else:
        print("Glossary file not found. Exiting.")
        return
    
    print(f"Glossary file found with {len(glossary)} entries.")

    # Load or initialize the staging file
    if os.path.exists(staging_file):
        with open(staging_file, 'r', encoding='utf-8') as sf:
            staging_data = json.load(sf)
    else:
        staging_data = {}

    # Resume processing from the last unprocessed chunk
    last_processed_chunk = max(int(key.split()[1]) for key in staging_data.keys()) if staging_data else 0

    previous_translation = "[No previous context available]"  # Initial value for the first chunk

    with tqdm(total=len(chunks), desc="Translating", initial=last_processed_chunk) as pbar:
        for chunk_idx, chunk in enumerate(chunks, start=1):
            if chunk_idx <= last_processed_chunk:
                previous_translation = staging_data.get(f"chunk {chunk_idx}", {}).get("English", previous_translation)
                pbar.update(1)
                continue

            glossary_subset = filter_glossary_for_chunk(chunk, glossary)
            glossary_text = "\n".join([f'"{key}": "{", ".join(values)}"' for key, values in glossary_subset.items()])
            retries = 0
            valid_response = False
            retry_reasons = []
            retry_message = ""

            while retries < max_retries and not valid_response:
                prompt = generate_translation_prompt(previous_translation, chunk, glossary_text)
                response = generate_response(prompt + f"\n{retry_message}", model)
                validity = translation_validity(response, glossary_subset)

                if validity == "AllGood":
                    valid_response = True
                    previous_translation = response.strip().split('\n')[-1]
                else:
                    if validity != "Error":
                        retry_reasons.append(validity)  # Log the failure reason
                        retry_message = failure[validity]
                    retries += 1
                    logging.info(f"Chunk {chunk_idx}: Retry {retries}/{max_retries} - Failure reason: {validity}")

            # Log the final result for the chunk
            if valid_response:
                logging.info(f"Chunk {chunk_idx}: Success after {retries + 1} attempts. Retry reasons: {retry_reasons}")
                staging_data[f"chunk {chunk_idx}"] = {
                    "Chinese": chunk,
                    "English": response,
                    "Glossary": glossary_subset
                }
            else:
                logging.info(f"Chunk {chunk_idx}: Failed after {max_retries} attempts. Retry reasons: {retry_reasons}")
                staging_data[f"chunk {chunk_idx}"] = {
                    "Chinese": chunk,
                    "English": "ERROR",
                    "Glossary": glossary_subset
                }

            with open(staging_file, 'w', encoding='utf-8') as sf:
                json.dump(staging_data, sf, ensure_ascii=False, indent=4)

            pbar.update(1)
    
    # Updating final txt
    extract_english_sections(staging_file, output_file)

if __name__ == "__main__":
    input_file = "Chinese_Section.txt"
    glossary_file = "glossary.json"
    staging_file = "mapping.json"
    output_file = "English.txt"

    process_file(input_file, glossary_file, staging_file, output_file, tokens_per_chunk=1000, max_retries=5)
    print("\nTranslation complete. Check mapping.json for results.")
