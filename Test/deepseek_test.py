import requests
import json
import time

def generate_response(prompt, model="deepseek-r1:8b", url="http://localhost:11434/api/generate"):
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
    start = time.time()
    prompt_text = "Give me a good investment strategy in Indian stock markets. This should be suitable for a beginner with moderate to high risk appetite, and require minimal effort."
    response = generate_response(prompt_text)
    print("Model Response:", response)
    print("Time taken: ", time.time() - start)
