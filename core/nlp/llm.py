from transformers import pipeline

generator = pipeline("text-generation", model="EleutherAI/gpt-neo-1.3B")
print(generator("Explain AI to a 5-year-old:", max_length=50))
