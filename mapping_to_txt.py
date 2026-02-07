import json

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

# Specify the input and output file names
mapping_file = "mapping.json"
output_file = "English.txt"

# Call the function
extract_english_sections(mapping_file, output_file)
