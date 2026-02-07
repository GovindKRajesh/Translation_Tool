import json
import os
from tqdm import tqdm
from aya_translate_v6 import generate_translation_prompt, generate_response, translation_validity

failure = {
    "Incomplete": "Your previous attempt failed because you provided an incomplete translation - Chinese text was found within the output. This time, ensure that your output is entirely in English.",
    "Preceding": "Your previous attempt failed because you provided preceding text within the output. This time, make sure to directly start outputing the translation without giving any text before it."
}

def retry_failed_chunks(staging_file="mapping.json", max_retries=3):
    if not os.path.exists(staging_file):
        print(f"Staging file {staging_file} not found. Exiting.")
        return

    # Load the staging file
    with open(staging_file, 'r', encoding='utf-8') as sf:
        staging_data = json.load(sf)

    # Find chunks with "ERROR" in the English field
    failed_chunks = {key: value for key, value in staging_data.items() if value.get("English") == "ERROR"}

    if not failed_chunks:
        print("No failed chunks found. Exiting.")
        return

    print(f"Found {len(failed_chunks)} failed chunks. Retrying...")
    updated_chunks = 0

    with tqdm(total=len(failed_chunks), desc="Retrying failed chunks") as pbar:
        for chunk_key, chunk_data in failed_chunks.items():
            retries = 0
            valid_response = False
            retry_reasons = []
            retry_message = ""

            while retries < max_retries and not valid_response:
                glossary_text = "\n".join([f'"{key}": "{", ".join(values)}"' for key, values in chunk_data.get("Glossary", {}).items()])
                previous_chunk_key = f"chunk {int(chunk_key.split()[1]) - 1}"
                prompt = generate_translation_prompt(
                    previous_translation = staging_data.get(previous_chunk_key, {}).get("English", "[No previous context available]"),
                    current_chunk=chunk_data["Chinese"],
                    glossary_text=glossary_text
                )

                response = generate_response(prompt + f"\n{retry_message}")
                validity = translation_validity(response)

                if validity == "AllGood":
                    valid_response = True
                    chunk_data["English"] = response.strip()  # Update with corrected translation
                else:
                    retry_reasons.append(validity)
                    if validity != "Error":
                        retry_message = failure[validity]
                    retries += 1

            # Log success or final failure
            if valid_response:
                print(f"\n{chunk_key}: Success after {retries + 1} attempts.")
                updated_chunks += 1
            else:
                print(f"\n{chunk_key}: Failed after {max_retries} attempts. Reasons: {retry_reasons}")

            # Update the staging file with the corrected or failed chunk
            staging_data[chunk_key] = chunk_data

            # Save progress after each chunk to avoid data loss
            with open(staging_file, 'w', encoding='utf-8') as sf:
                json.dump(staging_data, sf, ensure_ascii=False, indent=4)

            pbar.update(1)

    print(f"\nRetry process complete. {updated_chunks} chunks successfully corrected out of {len(failed_chunks)}.")

if __name__ == "__main__":
    staging_file = "mapping.json"
    retry_failed_chunks(staging_file=staging_file)
