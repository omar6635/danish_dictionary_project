import json


with open("dictionary_entries_cache.json", "w") as file:
  for i in range(3):
    file.write(json.dumps({}) + "\n")
  file.seek(0, 2)
  file.truncate(file.tell() - 1)
    