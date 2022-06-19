import configparser
import enum
import hashlib
import json
import math
import os
import sys
from collections import defaultdict
from os.path import join, getsize, realpath, relpath, normpath


class FileSizeUnit(enum.Enum):
    B = 'b'
    KB = 'kb'
    MB = 'mb'
    GB = 'gb'
    TB = 'tb'
    PB = 'pb'

    @staticmethod
    def from_str(text: str):
        if text.lower() == 'b':
            return FileSizeUnit.B
        elif text.lower() == 'kb':
            return FileSizeUnit.KB
        elif text.lower() == 'mb':
            return FileSizeUnit.MB
        elif text.lower() == 'gb':
            return FileSizeUnit.GB
        elif text.lower() == 'tb':
            return FileSizeUnit.TB
        elif text.lower() == 'pb':
            return FileSizeUnit.PB


def convert_to_bytes(size: float, unit: FileSizeUnit) -> int:
    if unit == FileSizeUnit.KB:
        return int(size * 1024)
    elif unit == FileSizeUnit.MB:
        return int(size * 1024 * 1024)
    elif unit == FileSizeUnit.GB:
        return int(size * 1024 * 1024 * 1024)
    elif unit == FileSizeUnit.TB:
        return int(size * 1024 * 1024 * 1024 * 1024)
    elif unit == FileSizeUnit.PB:
        return int(size * 1024 * 1024 * 1024 * 1024 * 1024)
    else:
        return int(size)


def get_chunks(file, chunk_size=1024) -> str:
    while True:
        chunk = file.read(chunk_size)
        if not chunk:
            return
        yield chunk


def get_hash(file_name, first_chunk: bool = False, chunk_size: int = 1024):
    hash_obj = hashlib.sha512()
    with open(file_name, 'rb') as file:
        if first_chunk:
            hash_obj.update(file.read(chunk_size))
        else:
            for chunk in get_chunks(file, chunk_size):
                hash_obj.update(chunk)
    return hash_obj.digest()


def find_duplicates(paths: list[str]) -> None:
    config = configparser.ConfigParser()
    config.read('search_rules.ini')

    file_list = list()
    print('Retrieving all files recursively...')
    for path in paths:
        recursive = bool(config.getboolean('General', 'Recursive'))
        excluded_dirs = [normpath(path) for path in json.loads(config.get('Filter', 'ExcludedDirectories'))]
        for dirpath, dirname, filenames in os.walk(path, topdown=True):
            dirname[:] = [d for d in dirname if join(dirpath, d) not in excluded_dirs]

            for name in filenames:
                extensions_tuple = tuple(json.loads(config.get('Filter', 'IncludeFileExtensions')))

                if len(extensions_tuple) > 0:
                    if name.endswith(extensions_tuple):
                        file_list.append(join(dirpath, name))
                else:
                    extensions_tuple = tuple(json.loads(config.get('Filter', 'ExcludeFileExtensions')))
                    if not name.endswith(extensions_tuple):
                        file_list.append(join(dirpath, name))

            if not recursive:
                break

        # Create dict of each file size with a list of files having that size
        size_dict = defaultdict(list)
        print('Getting file sizes...')
        for file_path in file_list:
            try:
                file_size = getsize(realpath(file_path))
                file_size_unit = FileSizeUnit.from_str(config.get('Filter', 'FileSizeUnit'))
                file_size_eq = config.get('Filter', 'FileSizeEqualTo')
                file_size_gt = config.get('Filter', 'FileSizeGreaterThan')
                file_size_lt = config.get('Filter', 'FileSizeLessThan')

                if file_size_eq:
                    file_size_eq = convert_to_bytes(float(file_size_eq), file_size_unit)
                    if file_size == file_size_eq:
                        size_dict[file_size].append(file_path)
                else:
                    file_size_gt = convert_to_bytes(float(file_size_gt), file_size_unit) if file_size_gt else -math.inf
                    file_size_lt = convert_to_bytes(float(file_size_lt), file_size_unit) if file_size_lt else math.inf

                    if file_size_gt < file_size < file_size_lt:
                        size_dict[file_size].append(file_path)
            except OSError:
                print('Unable to access file: ' + file_path)
                continue

        small_hash_dict = defaultdict(list)
        chunk_size = config.getint('General', 'ChunkSize')
        print('Checking first 1024 bytes...')
        counter = 0
        for size, file_list in size_dict.items():
            if len(file_list) < 2:
                continue

            for file_path in file_list:
                counter += 1
                try:
                    chunk_hash = get_hash(file_path, first_chunk=True, chunk_size=chunk_size)
                    small_hash_dict[(chunk_hash, size)].append(file_path)
                except OSError:
                    print('Unable to access file: ' + file_path)
                    continue
        print('{} files with identical sizes'.format(counter))

        hash_dict = dict()
        print('Calculating full hashes')
        for (_, _), file_list in small_hash_dict.items():
            if len(file_list) < 2:
                continue

            for file_path in file_list:
                try:
                    full_hash = get_hash(file_path, chunk_size=chunk_size)
                    if full_hash in hash_dict.keys():
                        file_path = relpath(file_path, start=path)
                        duplicate = relpath(hash_dict[full_hash], start=path)
                        print('Duplicate found: {} and {}'.format(file_path, duplicate))
                    else:
                        hash_dict[full_hash] = file_path
                except OSError:
                    print('Unable to access file: ' + file_path)
                    continue


def main():
    if sys.argv[1:]:
        find_duplicates(sys.argv[1:])
    else:
        with open('paths.txt', 'r') as paths_list:
            paths_list = paths_list.read().split('\n')
            find_duplicates(paths_list)


if __name__ == "__main__":
    main()
