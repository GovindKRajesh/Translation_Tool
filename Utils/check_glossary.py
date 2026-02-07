import re
import json

# Load the glossary
with open('glossary.json', 'r', encoding='utf-8') as json_file:
    glossary = json.load(json_file)

# Load the Chinese text file
with open('Chinese.txt', 'r', encoding='utf-8') as txt_file:
    chinese_text = txt_file.read()

# Extract text within 【】 brackets
bracketed_texts = re.findall(r'【(.*?)】', chinese_text)

# Check if all bracketed texts are in the glossary keys
missing_keys = [text for text in bracketed_texts if text not in glossary]

if missing_keys:
    for key in set(missing_keys):
        print(key)
else:
    print("All bracketed texts are present in the glossary.")