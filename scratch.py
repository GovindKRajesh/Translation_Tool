import json
import re

def check_glossary_consistency(staging_file):
    """
    Checks if the English translations in mapping.json include all glossary terms.
    Outputs chunks with missing glossary key-value pairs.
    """
    if not staging_file:
        print(f"Staging file {staging_file} not found. Exiting.")
        return

    # Load the staging file
    with open(staging_file, 'r', encoding='utf-8') as sf:
        staging_data = json.load(sf)

    problematic_chunks = []

    # Regular expression to detect glossary key in English section
    def is_term_present(english_text, term):
        pattern = re.escape(term)  # Escape special characters for exact matching
        return re.search(pattern, english_text, re.IGNORECASE)

    # Iterate over chunks and check for glossary consistency
    for chunk_key, chunk_data in staging_data.items():
        english_text = chunk_data.get("English", "")
        glossary = chunk_data.get("Glossary", {})

        missing_terms = []
        for term, translations in glossary.items():
            # Check if any translation for the term exists in the English text
            if not any(is_term_present(english_text, translation) for translation in translations):
                missing_terms.append({term: translations})

        if missing_terms:
            problematic_chunks.append({"chunk": chunk_key, "missing_terms": missing_terms})

    # Output the problematic chunks
    if problematic_chunks:
        print("Chunks with missing glossary terms:")
        for problem in problematic_chunks[:10]:
            print(f"Chunk: {problem['chunk']}")
            for missing_term in problem["missing_terms"]:
                for term, translations in missing_term.items():
                    print(f"  - Missing Term: {term}, Possible Translations: {translations}")
        print(f"Number of problematic chunks: {len(problematic_chunks)}")
    else:
        print("All chunks are consistent with the glossary.")

if __name__ == "__main__":
    check_glossary_consistency(staging_file="mapping.json")
