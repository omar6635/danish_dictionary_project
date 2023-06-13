import re
import json
from itertools import groupby
from bs4 import BeautifulSoup

return_dicts = []
lydfiler_dict = {}
udtale_dict = {}
pattern = r'\{.*\}'
with open("dictionary_entries_cache.json", "r") as file:
    content = file.read()
with open("audio_binaries", "rb") as file:
    audio_content = file.readlines()
dicts_array = re.findall(pattern, content)
dicts_array = [json.loads(my_dict) for my_dict in dicts_array]

for key, value in dicts_array[0].items():
    udtale_dict[key] = []
    for value_dict in value:
        tag = BeautifulSoup(value_dict["tag"], 'html.parser').find()
        prev_tag = BeautifulSoup(value_dict["prev_sib"], 'html.parser').find()
        tag.previous_sibling = prev_tag
        udtale_dict[key].append(tag)
formatted_binaries = [
    line[2:-2] if i != len(audio_content) - 1 else line[2:-1]
    for i, line in enumerate(audio_content)
]
formatted_binaries = [
    list(group)
    for key, group in groupby(formatted_binaries, lambda x: x == b"")
    if not key
]
for audio_binary_list, (key, value) in zip(formatted_binaries,
                                           dicts_array[1].items()):
    lydfiler_dict[key] = []
    for audio_binary in audio_binary_list:
        lydfiler_dict[key].append(audio_binary)

return_dicts.extend([udtale_dict, lydfiler_dict, dicts_array[2]])
