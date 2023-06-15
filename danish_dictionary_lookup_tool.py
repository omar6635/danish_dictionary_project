import sys
import re
import json
import base64

import urllib.error
import urllib.request
import requests
import pygame

from itertools import groupby
from urllib.parse import quote
from bs4 import BeautifulSoup
from bs4 import element


def find_nonredundant_keys(dict1: dict) -> (list, bool):
    with open("dictionary_entries_cache.txt", "r") as file:
        dict2 = json.loads(file.readlines()[2])
    if set(dict1.keys()).issubset(set(dict2.keys())):
        return False
    else:
        nonredundant_keys = set(dict1.keys()) - set(dict2.keys())
    return list(nonredundant_keys)


def delete_entry(command: str, dicts: list) -> None:
    if len(command.split("-")) > 1:
        if command.split("-")[1].strip() == "all":
            for my_dict in dicts:
                my_dict.clear()
            delete_all_items()
        elif command.split("-")[1].strip().isalnum():
            key = command.split("-")[1].strip()
            try:
                for my_dict in dicts:
                    my_dict.pop(key)
            except KeyError:
                print("Kunne ikke finde ordet. Gennemgå ordlisten!")
            delete_one_item(key=key)
    else:
        for my_dict in dicts:
            my_dict.popitem()
        delete_one_item(del_last=True)


def delete_one_item(key: str = "", del_last: bool = False) -> None:
    all_dicts = get_dicts_cache()
    transcription_dict = get_transcriptions(all_dicts[0])
    audios_dict = get_audio_binaries(all_dicts[1])
    meanings_dict = all_dicts[2]
    try:
        if del_last:
            last_item = transcription_dict.popitem()[0]
            meanings_dict.pop(last_item)
            audios_dict.pop(last_item)
        elif key:
            transcription_dict.pop(key)
            meanings_dict.pop(key)
            audios_dict.pop(key)
    except KeyError:
        pass
    finally:
        delete_all_items()
        append_dicts_cache([transcription_dict, audios_dict, meanings_dict])


def clear_dicts_cache():
    with open("dictionary_entries_cache.txt", "w") as file:
        for i in range(3):
            file.write(json.dumps({}) + "\n")
        file.seek(0, 2)
        file.truncate(file.tell() - 1)


def delete_all_items() -> None:
    with open("audio_binaries", "wb") as file2:
        clear_dicts_cache()
        file2.write(b"")


def fetch_html_file(user_input: str) -> (BeautifulSoup, None):
    try:
        u_p = user_input.strip()
        query = fetch_url(
            quote("https://ordnet.dk/ddo_en/dict?query=" + u_p, safe=':/?=&'))
        bs_obj = BeautifulSoup(query.read(), 'html.parser')
        bs_conflicts = find_conflicts(bs_obj)
        return bs_conflicts if bs_conflicts else bs_obj
    except (urllib.error.URLError, urllib.error.HTTPError) as e:
        raise e


def fetch_url(url: str):
    response = urllib.request.urlopen(url)
    return response


def find_betydninger(bs_obj: BeautifulSoup, betydninger: dict) -> None:
    betydninger_instances = bs_obj.find("div", id="content-betydninger").find_all(
        class_="definitionIndent", recursive=False)
    entries_dict = {}
    for i, instance in enumerate(betydninger_instances):
        definition = instance.find(class_="definition").text
        examples = instance.find("span", class_="stempel", string="Eksempler")
        synonyms = instance.find("span", class_="stempel", string="Synonymer")
        entries_dict[f"ENTRY {i + 1}"] = [str(definition)]
        if examples:
            examples = examples.find_next_sibling("span").text
            examples = ','.join(examples.split("\xa0")).replace("\xa0", "")
            entries_dict[f"ENTRY {i + 1}"].append(str(examples))
        if synonyms:
            synonyms = synonyms.find_next_sibling("span").text
            synonyms = ', '.join(synonyms.split()).replace("\xa0", "")
            entries_dict[f"ENTRY {i + 1}"].append(str(synonyms))
    betydninger[bs_obj.find("span", class_="match").text] = entries_dict


def find_conflicts(html_file: BeautifulSoup) -> (BeautifulSoup, None):
    div_tags = html_file.find(class_="searchResultBox").find_all("div")
    if len(div_tags) > 1:
        a_tags = [my_element.find("a") for my_element in div_tags]
        div_tags_text = [
            div_element.text.replace(a_element.text.strip(), "").strip()
            for a_element, div_element in zip(a_tags, div_tags)
        ]

        # print all the found entries using a list comprehension
        [
            print(f"{i + 1}) {a_text.text.strip()} ({d_text})")
            for i, (a_text, d_text) in enumerate(zip(a_tags, div_tags_text))
        ]
        print(
            "Der er fundet flere poster, vælg venligst én ved at indtaste et tal."
        )

        # take the user's choice
        while True:
            user_choice = input("-> ")
            if not user_choice.isnumeric() or int(user_choice) > len(
                    a_tags) or int(user_choice) <= 0:
                print("Dette nummer er ikke på listen, prøv venligst igen!")
            else:
                break
        bs_obj = BeautifulSoup(
            fetch_url(
                quote(a_tags[int(user_choice) - 1]["href"],
                      safe=':/?=&,')).read(), 'html.parser')
        return bs_obj
    return None


def find_lydfiler(bs_obj: BeautifulSoup, lydfiler: dict):
    audio_ids = [
        audio["id"] if audio else None for audio in bs_obj.find(id="id-udt").find_all("audio")
    ]
    anchor_elements = [
        bs_obj.find(id="id-udt").find(id=id_element + "_fallback")
        for id_element in audio_ids
    ]
    hrefs = [my_element["href"] for my_element in anchor_elements]
    lydfiler[bs_obj.find("span", class_="match").text] = []
    [
        lydfiler[bs_obj.find("span", class_="match").text].append(
            requests.get(href).content) for href in hrefs
    ]


def find_udtale(bs_obj: BeautifulSoup, udtale_transcriptions: dict) -> None:
    udtale_instances = bs_obj.find(id="id-udt").find_all("span",
                                                         class_="lydskrift")
    udtale_instances = [instance for instance in udtale_instances]
    udtale_transcriptions[bs_obj.find("span",
                                      class_="match").text] = udtale_instances


def play_audio(audios):
    for key_values_pair in audios:
        for value in key_values_pair[1]:
            with open("audio.mp3", "wb") as audio_file:
                audio_file.write(value)
                audio_file.flush()
            sound = pygame.mixer.Sound("audio.mp3")
            channel = pygame.mixer.Channel(0)
            channel.play(sound)
            while channel.get_busy():
                pygame.time.delay(100)
            pygame.mixer.music.stop()


def print_meaning_dict(key_value_list: list) -> None:
    for key, meaning in key_value_list:
        print(f"\t{key}")
        try:
            print(f"\t\tBetydning: {meaning[0]}")
            print(f"\t\tEksempler: {meaning[1]}")
            print(f"\t\tSynonymer: {meaning[2]}")
        except IndexError:
            continue


def print_meanings(command: str, meanings_dict: dict):
    split_command = command.split("-")
    if len(split_command) > 1 and split_command[1].strip().isalnum():
        specific_word = split_command[1].strip()
        print(specific_word.upper())
        print_meaning_dict(meanings_dict[specific_word].items())
    else:
        for name, entry in meanings_dict.items():
            print(f"{name.upper()}")
            print_meaning_dict(entry.items())


def print_transcription_values(transcription_list):
    for transcription in transcription_list:
        print("\t", end="")
        if transcription.find_previous_sibling('span') is None:
            print("udtale", end=": ")
        else:
            print(
                transcription.find_previous_sibling('span').text.split(":")[0],
                end=": ")
        print(transcription.text)


def print_transcriptions(command: str, transcription_dict: dict):
    if len(command.split("-")) < 2:
        for key, value in transcription_dict.items():
            try:
                print(key.upper() + ":")
                print_transcription_values(value)
            except AttributeError:
                print("kunne ikke hente orddata")
    elif command.split("-")[1].strip().isalnum():
        try:
            key = command.split("-")[1].strip().lower()
            value = transcription_dict.get(key)
            print(key.upper() + ":")
            print_transcription_values(value)
        except (TypeError, AttributeError):
            print("Kunne ikke finde nogen data for dette ord")


def process_flag_audio(command: str, audios_dict: dict):
    if len(command.split("-")) > 1:
        try:
            if command.split("-")[1].strip() == "p":
                play_audio([(key, value[:1])
                            for key, value in audios_dict.items()])
            elif command.split("-")[1].strip().isalnum():
                key = command.split("-")[1].strip().lower()
                value = audios_dict.get(key)
                if len(command.split("-")) > 2 and command.split(
                        "-")[2].strip() == "p":
                    play_audio([(key, [value[0]])])
                else:
                    play_audio([(key, value)])
        except TypeError:
            print("kunne ikke hente data til denne lyd")
    else:
        play_audio(list(audios_dict.items()))


def read_dicts():
    dicts_array = get_dicts_cache()
    return [get_transcriptions(dicts_array[0]), get_audio_binaries(dicts_array[1]), dicts_array[2]]


def get_dicts_cache() -> list:
    with open("dictionary_entries_cache.txt", "r") as file:
        content = file.read()
    pattern = r'\{.*\}'
    dicts_array = re.findall(pattern, content)
    dicts_array = [json.loads(my_dict) for my_dict in dicts_array]
    return dicts_array


def get_transcriptions(transcriptions: dict) -> dict:
    return_dict = {}
    for key, value in transcriptions.items():
        return_dict[key] = []
        for value_dict in value:
            tag = BeautifulSoup(value_dict["tag"], 'html.parser').find()
            prev_tag = BeautifulSoup(value_dict["prev_sib"], 'html.parser').find()
            tag.previous_sibling = prev_tag
            return_dict[key].append(tag)
    return return_dict


def get_audio_binaries(keys_dict: dict) -> dict:
    with open("audio_binaries", "rb") as file:
        binaries = file.readlines()
    return_dict = {}
    formatted_binaries = [line for i, line in enumerate(binaries) if line != b'']
    formatted_binaries = [
        list(group)
        for key, group in groupby(formatted_binaries, lambda x: x == b"\n")
        if not key
    ]
    for audio_binary_list, (key, value) in zip(formatted_binaries, keys_dict.items()):
        return_dict[key] = []
        for audio_binary in audio_binary_list:
            return_dict[key].append(base64.b64decode(audio_binary))
    return return_dict


def serialize_dicts(local: dict, remote: str, file, audio_file):
    if isinstance(list(local.values())[0], list) and isinstance(list(local.values())[0][0], bytes):
        remote_deserialized = json.loads(remote)
        key_no_value_local = {key: [] for key in local}
        remote_deserialized.update(key_no_value_local)
        file.write(json.dumps(remote_deserialized) + "\n")
        for value in list(local.values()):
            for subvalue in value:
                audio_file.write(base64.b64encode(subvalue))
                audio_file.write(b"\n")
            audio_file.write(b"\n")
    else:
        remote_deserialized = json.loads(remote)
        if isinstance(list(local.values())[0], list) and isinstance(
                list(local.values())[0][0], element.Tag):
            local = {
                key: [{
                    "tag": str(subvalue),
                    "prev_sib": str(subvalue.find_previous_sibling())
                } for subvalue in value]
                for key, value in local.items()
            }
        remote_deserialized.update(local)
        file.write(json.dumps(remote_deserialized) + "\n")


def append_dicts_cache(dicts: list):
    with open("dictionary_entries_cache.txt", "r+") as file, open("audio_binaries", "ab+") as audio_file:
        dicts_serialized = file.readlines()
        file.seek(0)
        for my_dict_local, my_dict_remote in zip(dicts, dicts_serialized):
            try:
                serialize_dicts(my_dict_local, my_dict_remote, file, audio_file)
            except IndexError:
                file.write(json.dumps({}) + "\n")
        file.seek(0, 2)
        file.truncate(file.tell() - 1)


def main():
    cached_dicts = read_dicts()
    udtale_transcriptions, lydfiler, betydninger = cached_dicts
    while True:
        user_input = input(
            "indtast ord, du gerne vil slå op i den danske ordbog:\n-> ")
        while user_input != "":
            try:
                query = fetch_html_file(user_input)
            except (urllib.error.URLError, urllib.error.HTTPError) as e:
                print(e)
            else:
                if query:
                    try:
                        find_udtale(query, udtale_transcriptions)
                        find_betydninger(query, betydninger)
                        find_lydfiler(query, lydfiler)
                    except AttributeError:
                        print("Kunne ikke finde data om ordet")
            user_input = input("-> ")

        keys = find_nonredundant_keys(betydninger)
        if keys:
            recon_udt = {key: udtale_transcriptions[key] for key in keys if key in udtale_transcriptions}
            recon_lyd = {key: lydfiler[key] for key in keys if key in lydfiler}
            recon_bty = {key: betydninger[key] for key in keys if key in betydninger}
            append_dicts_cache([recon_udt, recon_lyd, recon_bty])
        command = False

        while True:
            if command is False:
                command = input(
                    "Hvad vil du gerne gøre nu?\n1. transskriptioner\n2. udtaler [-p]|[-(ord)]"
                    "\n3. begge [-p]|[-(ord)]\n4. betydninger \n5. afslut program"
                    "\n6. genstart programmet\n7. slette post(er)\n-> ")
            else:
                command = input("-> ")
            if command.split("-")[0].strip() == "1":
                print_transcriptions(command, udtale_transcriptions)
            elif command.split("-")[0].strip() == "2":
                process_flag_audio(command, lydfiler)
            elif command.split("-")[0].strip() == "3":
                print_transcriptions(command, udtale_transcriptions)
                process_flag_audio(command, lydfiler)
            elif command.split("-")[0].strip() == "4":
                print_meanings(command, betydninger)
            elif command.strip() == "5":
                print("tak fordi du brugte programmet!")
                sys.exit(0)
            elif command.strip() == "6":
                break
            elif command.split("-")[0].strip() == "7":
                delete_entry(command,
                             [udtale_transcriptions, lydfiler, betydninger])
            else:
                print(
                    "Beklager, du skal indtaste et af de tre tal. Prøv igen!")
                continue


if __name__ == "__main__":
    pygame.mixer.init()
    main()
