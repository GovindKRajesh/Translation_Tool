import json
import os
import re
import time
import logging
from tqdm import tqdm
import google.generativeai as genai
from dotenv import load_dotenv

logging.basicConfig(
    filename='refining_log.log',
    level=logging.INFO,
    format='%(asctime)s - %(message)s',
    datefmt='%Y-%m-%d %H:%M:%S'
)

load_dotenv()
gemini_key = os.environ["GEMINI_KEY"]

system_message = """
    You are a highly skilled editor with expert level knowledge of both English and Chinese.
    You will be provided with two chunks of text - the original Chinese text, as well as the basic English translation of the said text.
    Alongside this, you will be provided with the glossary of terms, as well as the previous translated chunk for context.
    Your role is to proofread the English translation, compare it against the original Chinese text, and rewrite the English version so that it may be consistent with the original, as well as with the glossary.
    The text you are provided (both Chinese and English) are from the Light Novel Danmachi (Dungeon ni Deai wo Motomeru no wa Machigatteiru Darou ka / Is It Wrong to Try to Pick Up Girls in a Dungeon?). You are free to use your knowledge of this work to enhance your editing.
    You must ensure that the chunk of text you are returning flows perfectly from the previous chunk.
    Your response must be consistent with the original Chinese text, and should not paraphrase or summarize anything mentioned there. The goal is to obtain a high-quality and readable translation. 
    Make sure that the output flows well, with proper spacing and avoiding repetition unless present in the original Chinese.
    Only output the edited English text, nothing else. Your response will directly be appended to the final translated copy, so there must be no preceding or following text.
    Do not use markdown in your response. Instead, use double quotes for speech, and 「」 brackets for any special terms, the same way as they are used in the original Chinese text.
    Ensure that you have proper line and paragraph formatting and spacing, so that the text would be easily readable if pushed to a PDF file. Your response must be entirely English, without any Chinese.
    Any headings or chapter names should be marked with a hash (#) in front of it for easy identification.
    """

def generate_editing_prompt(previous_chunk, current_chunk_cn, current_chunk_en, glossary_text):    
    return f"""
Glossary:
{glossary_text}

------------------

Here is the previous chunk, so that you may continue from there. Maintain the same formatting as this chunk in your response:
{previous_chunk}

------------------

This is the original Chinese text:
{current_chunk_cn}

------------------

This is the basic English translation of the above Chinese text:
{current_chunk_en}

------------------

Now, generate the edited English text as per the instructions.
    """

def generate_response(prompt, model="gemini-2.0-flash-thinking-exp-01-21"):
    genai.configure(api_key=gemini_key)
    model_instance = genai.GenerativeModel(model_name=model, system_instruction=system_message)
    max_retries = 15
    delay = 10
    for attempt in range(1, max_retries + 1):
        try:
            response = model_instance.generate_content(prompt)
            if hasattr(response, "candidates") and len(response.candidates) > 0:
                if hasattr(response.candidates[0].content, "parts"):
                    output = response.candidates[0].content.parts[0].text
                    if translation_validity(output):
                        logging.info("Success")
                        return output
            raise Exception("Invalid response structure or content")

        except Exception as e:
            if attempt < max_retries:
                logging.info(f"Attempt {attempt} failed: {e}. Retrying in {delay} seconds...")
                time.sleep(delay)
            else:
                logging.info(f"Attempt {attempt} failed: {e}. No more retries left.")
                return "ERROR"

def translation_validity(response):
    try:
        # Check if the text contains Chinese characters
        chinese_characters = re.search(r'[\u4e00-\u9fff]', response)
        if chinese_characters:
            return "Incomplete"
        
        # Check for the word 'translation' to detect preceding explanatory text
        if "translation" in response.lower():
            return "Preceding"
            
        return "AllGood"
    except Exception as e:
        logging.info(f"Error when checking validity: {e}")
        return "Error"

def process_chunks(staging_file, output_file):
    if not os.path.exists(staging_file):
        print(f"Error: {staging_file} does not exist.")
        return
    with open(staging_file, 'r', encoding='utf-8') as sf:
        staging_data = json.load(sf)
    error_flag = False
    sorted_chunk_keys = sorted(staging_data.keys(), key=lambda x: int(x.split()[1]))
    previous = "This is the first chunk"
    
    with tqdm(total=len(sorted_chunk_keys), desc="Processing Chunks") as pbar:
        for chunk_key in sorted_chunk_keys:
            chunk = staging_data[chunk_key]
            if "Refined" in chunk and chunk.get("Refined", "") != "ERROR":
                pbar.update(1)
                continue
            logging.info(f"Starting process for {chunk_key}")
            if chunk_key != "chunk 1":
                previous = staging_data["chunk " + str(int(chunk_key.split()[1]) - 1)]["Refined"]
            prompt = generate_editing_prompt(
                previous,
                chunk["Chinese"],
                chunk["English"],
                chunk["Glossary"]
            )
            response = generate_response(prompt)
            previous = response
            chunk["Refined"] = response
            if response == "ERROR":
                error_flag = True
            with open(staging_file, 'w', encoding='utf-8') as sf:
                json.dump(staging_data, sf, ensure_ascii=False, indent=4)
            pbar.update(1)
    if not error_flag:
        with open(output_file, 'w', encoding='utf-8') as out:
            for chunk_key in sorted_chunk_keys:
                refined_text = staging_data[chunk_key].get("Refined", "")
                if refined_text and refined_text != "ERROR":
                    out.write(refined_text + '\n')
        print("Processing complete. English.txt updated.")
    else:
        print("Completed with error(s). Rerun to plug gaps.")

def main():
    staging_file = "mapping.json"
    output_file = "English.txt"
    process_chunks(staging_file, output_file)

if __name__ == "__main__":
    main()