import re

string = '{"key1": {"key2": "value2"}, "key3": {"key4": "value4"}}'
# using positive lookahead and lookbehind assertions.
# lookbehind: (?<=...)
# lookahead: (?=...) 
match = re.search(r'(?<={)[^{}]*(?=})', string)
if match:
    extracted_data = match.group(0)
    print("Extracted data:", extracted_data)
else:
    print("No match found.")
  