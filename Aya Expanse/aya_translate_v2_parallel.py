import aiohttp
import asyncio
import tiktoken
import json
from tqdm import tqdm
from prompt_utils import alt_prompt

base_prompt = alt_prompt

async def get_chunks(file_path, tokens_per_chunk=1000, encoding_name="cl100k_base"):
    tokenizer = tiktoken.get_encoding(encoding_name)
    
    with open(file_path, 'r', encoding='utf-8') as file:
        text = file.read()
    
    tokens = tokenizer.encode(text)
    total_tokens = len(tokens)
    print(f"Total number of tokens in the original file: {total_tokens}")
    
    chunks = [tokenizer.decode(tokens[i:i + tokens_per_chunk]) for i in range(0, len(tokens), tokens_per_chunk)]
    return chunks

async def generate_response(session, prompt, model="aya-expanse", url="http://localhost:11434/api/generate"):
    headers = {"Content-Type": "application/json"}
    payload = {
        "model": model,
        "prompt": base_prompt + prompt,
        "stream": False
    }

    async with session.post(url, headers=headers, data=json.dumps(payload)) as response:
        if response.status == 200:
            result = await response.json()
            return result.get("response", "No response field found in the API response.")
        else:
            return f"Error: {response.status}"

async def process_file(input_file, output_file, concurrency=10):
    chunks = await get_chunks(input_file)
    
    async with aiohttp.ClientSession() as session:
        tasks = []
        results = [None] * len(chunks)  # Pre-allocate a list to preserve order

        with tqdm(total=len(chunks), desc="Translating") as pbar:
            sem = asyncio.Semaphore(concurrency)

            async def process_chunk(index, chunk):
                async with sem:
                    response = await generate_response(session, chunk)
                    results[index] = response
                    pbar.update(1)

            for i, chunk in enumerate(chunks):
                task = asyncio.create_task(process_chunk(i, chunk))
                tasks.append(task)

            await asyncio.gather(*tasks)

        # Write results to the output file in the correct order
        with open(output_file, 'w', encoding='utf-8') as out_file:
            for result in results:
                out_file.write(result + "\n\n")

if __name__ == "__main__":
    input_file = "Chinese.txt"
    output_file = "English.txt"

    asyncio.run(process_file(input_file, output_file))
    print("Translation complete. Check English.txt for results.")
