from together import Together
from dotenv import load_dotenv
load_dotenv()


def chat_with_together(
        prompt: str,
        model: str = "meta-llama/Llama-3.3-70B-Instruct-Turbo-Free"
) -> str:
    try:
        client = Together()  # Uses TOGETHER_API_KEY from environment

        response = client.chat.completions.create(
            model=model,
            messages=[{"role": "user", "content": prompt}]
        )

        return response.choices[0].message.content

    except Exception as e:
        return f"❌ Error calling Together API: {e}"


print(chat_with_together("hello"))
