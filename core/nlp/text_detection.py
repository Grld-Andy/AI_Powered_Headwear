from transformers import pipeline

# Load models
fix_spelling = pipeline("text2text-generation", model="oliverguhr/spelling-correction-english-base")
fix_grammar = pipeline("text2text-generation", model="prithivida/grammar_error_correcter_v1")


def clean_text_pipeline(text):
    # Step 1: Spelling correction
    spelling_fixed = fix_spelling(text, max_new_tokens=512)[0]['generated_text'].strip()
    print("Spelling Corrected:", spelling_fixed)

    # Step 2: Grammar correction with fallback
    grammar_corrected = fix_grammar(spelling_fixed, max_new_tokens=512)[0]['generated_text'].strip()
    final = grammar_corrected if len(grammar_corrected.split()) > 3 else spelling_fixed

    return final


# Example usage
raw_ocr = "angel ups et HEALTH foe Revolutionizing Health and safety 4 tho Role of Ai and Digitallzation at tea Work."
print('Raw text: ', raw_ocr)
final_cleaned = clean_text_pipeline(raw_ocr)
print("\n✅ Final Cleaned Text:", final_cleaned)
