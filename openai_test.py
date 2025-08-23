from openai import OpenAI
from openai_config import OPENAI_API_KEY, OPENAI_MODEL, OPENAI_MAX_TOKENS, OPENAI_SEED

client = OpenAI(
  api_key=OPENAI_API_KEY
)

response = client.responses.create(
    model="gpt-5-nano",
    input="Víš co je to léková indikace?."
)

print(response.output_text)

