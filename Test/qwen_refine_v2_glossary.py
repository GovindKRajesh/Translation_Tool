import requests
import json
import tiktoken
from tqdm import tqdm
from sentence_transformers import SentenceTransformer, util

def generate_response(prompt, model="qwen2.5", url="http://localhost:11434/api/generate"):
    headers = {"Content-Type": "application/json"}
    payload = {
        "model": model,
        "prompt": prompt,
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


def get_chunks(file_path, tokens_per_chunk, encoding_name="cl100k_base"):
    tokenizer = tiktoken.get_encoding(encoding_name)
    with open(file_path, 'r', encoding='utf-8') as file:
        text = file.read()
    tokens = tokenizer.encode(text)
    total_tokens = len(tokens)
    print(f"Total number of tokens in the original file: {total_tokens}")
    
    chunks = [
        tokenizer.decode(tokens[i:i + tokens_per_chunk])
        for i in range(0, total_tokens, tokens_per_chunk)
    ]
    return chunks


def extract_relevant_glossary(glossary_path, chunk_text, model, similarity_threshold=0.8):
    # Load glossary
    with open(glossary_path, 'r', encoding="utf-8") as file:
        glossary = json.load(file)
    
    # Flatten glossary into key-value pairs with categories
    glossary_items = [
        (f"{category}: {name}", definition)
        for category, entries in glossary.items()
        for name, definition in entries.items()
    ]
    glossary_texts = [item[0] for item in glossary_items]
    glossary_definitions = [item[1] for item in glossary_items]

    # Perform direct substring matches
    substring_matches = set()
    for category, entries in glossary.items():
        for name, definition in entries.items():
            if category == "Organizations":
                # Match only the first word of organization names
                first_word = name.split()[0]
                if first_word in chunk_text:
                    substring_matches.add(f"{category}: {name}: {definition}")
            else:
                # Match full name or any part (first/last) for other categories
                name_parts = name.split()
                if any(part in chunk_text for part in name_parts):
                    substring_matches.add(f"{category}: {name}: {definition}")

    # Perform semantic similarity matches
    chunk_embedding = model.encode(chunk_text, convert_to_tensor=True)
    glossary_embeddings = model.encode(glossary_texts, convert_to_tensor=True)
    similarities = util.pytorch_cos_sim(chunk_embedding, glossary_embeddings)[0]
    
    semantic_matches = {
        f"{glossary_texts[idx]}: {glossary_definitions[idx]}"
        for idx in (similarities > similarity_threshold).nonzero(as_tuple=True)[0]
    }

    # Combine and deduplicate matches
    combined_matches = substring_matches.union(semantic_matches)
    refined_glossary = "\n".join(combined_matches)

    # Convert to a formatted string
    return refined_glossary


if __name__ == "__main__":
    # File paths
    input_file_path = 'English_v4.txt'
    glossary_file_path = 'refining_glossary.json'
    output_file_path = 'Refined_English.txt'

    # Load the embedding model
    embedding_model = SentenceTransformer('all-MiniLM-L6-v2')

    # Enhanced prompt
    refinement_prompt = """
    You are a highly skilled editor specializing in refining English text for readability and coherence.
    Your task is to improve the text provided below while strictly adhering to these rules:
    
    1. Retain all proper nouns and terminology as they are, unless they differ from the provided glossary - if they do, correct them to be consistent with the glossary.
    2. Avoid unnecessary paraphrasing or altering of text that is already clear and accurate.
    3. Remove redundancy, improve phrasing, and ensure natural flow, while preserving the original meaning.
    4. Use the glossary definitions provided below to handle proper nouns and terminology accurately.
    5. The meaning of the original text must be preserved, only the phrasing and flow can be altered to make the text easier to read.
    6. Any quotes or speech sections must be retained as such, and must not be paraphrased into regular text. However, the speech itself can be modified to make it clearer and flow better.
    7. You will be provided with the last part of where your previous response left off, so that you can continue directly from there. Avoid repetition.
    
    Glossary:
    """

    # Chunk the input file
    chunks = get_chunks(input_file_path, tokens_per_chunk=600)

    # Process each chunk and save results with a progress bar
    last_context = ""  # Stores the last 200-300 characters from the previous translation
    with open(output_file_path, 'w', encoding='utf-8') as output_file:
        with tqdm(total=len(chunks), desc="Processing Chunks") as progress_bar:
            for idx, chunk in enumerate(chunks):
                # Extract relevant glossary entries dynamically using semantic similarity
                glossary_text = extract_relevant_glossary(glossary_file_path, chunk, embedding_model)
                
                # Prepare context for the current chunk
                context_prompt = f"\n\nLast Context:\n{last_context}" if last_context else ""

                # Construct the full prompt
                prompt_text = f"{refinement_prompt}{glossary_text}{context_prompt}\n\nText to refine:\n{chunk}"
                
                # Generate the refined response
                response = generate_response(prompt_text)

                # Write the response to the output file
                output_file.write(f"{response}\n")

                # Update last_context with the last 200-300 characters of the current response
                last_context = response[-300:] if len(response) > 300 else response

                progress_bar.update(1)
    
    print(f"Refined text saved to {output_file_path}.")
