my_dict = {"key1": 1, "key2": 2, "key3": 3}
my_dict2 = {"key1": 1, "key2": 2, "key3": 3}
this_item = my_dict.popitem()[0]
my_dict2.pop(this_item)
print(my_dict)
