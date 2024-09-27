import tiktoken, json

tokenizer = tiktoken.get_encoding("o200k_base")
file = "nyaa4k.json"

a = 0
with open(file, encoding="utf-8") as f:
    d = json.load(f)
    for item in d:
        a += int(len(tokenizer.encode(item["text"])))

print(a)