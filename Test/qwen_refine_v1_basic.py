import requests
import json
from prompt_utils import simple_refine, refinement_prompt

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

if __name__ == "__main__":
    with open('English_v4.txt', "r", encoding="utf-8") as file:
        text = file.read(5000)
    prompt_text = refinement_prompt + text
    response = generate_response(prompt_text)
    print("Model Response:", response)
