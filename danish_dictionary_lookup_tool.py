import sys
import urllib
import requests
import pygame
import json
import base64
import re
from itertools import groupby
from urllib import error, request
from urllib.parse import quote
from bs4 import BeautifulSoup
from bs4 import element


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


def fetch_url(url):
    response = urllib.request.urlopen(url)
    return response


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


def find_conflicts(html_file: BeautifulSoup) -> (BeautifulSoup, None):
    div_tags = html_file.find(class_="searchResultBox").find_all("div")
    if len(div_tags) > 1:
        a_tags = [element.find("a") for element in div_tags]
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


def find_udtale(bs_obj: BeautifulSoup, udtale_transcriptions: dict) -> None:
    udtale_instances = bs_obj.find(id="id-udt").find_all("span",
                                                         class_="lydskrift")
    udtale_instances = [instance for instance in udtale_instances]
    udtale_transcriptions[bs_obj.find("span",
                                      class_="match").text] = udtale_instances


def find_betydninger(bs_obj: BeautifulSoup, betydninger: dict) -> None:
    betydninger_instances = bs_obj.find(
        "div", id="content-betydninger").find_all(class_="definitionIndent",
                                                  recursive=False)
    entries_dict = {}
    for i, instance in enumerate(betydninger_instances):
        definition = instance.find(class_="definition").text
        examples = instance.find("span", class_="stempel", string="Eksempler")
        synonyms = instance.find("span", class_="stempel", string="Synonymer")
        entries_dict[f"ENTRY {i+1}"] = [str(definition)]
        if examples:
            examples = examples.find_next_sibling("span").text
            examples = ','.join(examples.split("\xa0")).replace("\xa0", "")
            entries_dict[f"ENTRY {i+1}"].append(str(examples))
        if synonyms:
            synonyms = synonyms.find_next_sibling("span").text
            synonyms = ', '.join(synonyms.split()).replace("\xa0", "")
            entries_dict[f"ENTRY {i+1}"].append(str(synonyms))
    betydninger[bs_obj.find("span", class_="match").text] = entries_dict


def find_lydfiler(bs_obj: BeautifulSoup, lydfiler: dict):
    audio_ids = [
        audio["id"] for audio in bs_obj.find(id="id-udt").find_all("audio")
    ]
    anchor_elements = [
        bs_obj.find(id="id-udt").find(id=id_element + "_fallback")
        for id_element in audio_ids
    ]
    hrefs = [element["href"] for element in anchor_elements]
    lydfiler[bs_obj.find("span", class_="match").text] = []
    [
        lydfiler[bs_obj.find("span", class_="match").text].append(
            requests.get(href).content) for href in hrefs
    ]


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


def delete_entry(command: str, dicts: list) -> None:
    if len(command.split("-")) > 1:
        if command.split("-")[1].strip() == "all":
            for my_dict in dicts:
                my_dict.clear()
        elif command.split("-")[1].strip().isalnum():
            for my_dict in dicts:
                my_dict.pop(command.split("-")[1].strip())
    else:
        for my_dict in dicts:
            my_dict.popitem()


def print_meaning_dict(key_value_list: list) -> None:
    for key, meaning in key_value_list:
        print(f"\t{key}")
        try:
            print(f"\t\tBetydning: {meaning[0]}")
            print(f"\t\tEksempler: {meaning[1]}")
            print(f"\t\tSynonymer: {meaning[2]}")
        except IndexError:
            continue


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


def read_dicts():
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
    return return_dicts


def write_dicts(dicts: list):
    with open("dictionary_entries_cache.json", "r+") as file:
        dicts_serialized = file.readlines()
        file.seek(0)
        for my_dict_local, my_dict_remote in zip(dicts, dicts_serialized):
            serialize_dicts(my_dict_local, my_dict_remote, file)
        file.seek(0, 2)
        file.truncate(file.tell() - 1)


def serialize_dicts(local: dict, remote: dict, file):
    if isinstance(list(local.values())[0], list) and isinstance(
            list(local.values())[0][0], bytes):
        remote_deserialized = json.loads(remote)
        local = {key: [] for key in local}
        remote_deserialized.update(local)
        file.write(json.dumps(remote_deserialized) + "\n")
        with open("audio_binaries", "ab+") as audio_file:
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


def main():
    cached_dicts = read_dicts()
    udtale_transcriptions, betydninger, lydfiler = cached_dicts
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
                    else:
                        write_dicts(
                            [udtale_transcriptions, lydfiler, betydninger])
            user_input = input("-> ")

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
