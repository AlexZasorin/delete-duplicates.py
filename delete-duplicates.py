import hashlib
import os
import sys
from collections import defaultdict


def get_hash(file_name, first_chunk: bool = False, chunk_size: int = 1024):
    hash_obj = hashlib.sha512()
    with open(file_name, 'rb') as file:
        if first_chunk:
            hash_obj.update(file.read(chunk_size))
        else:
            hash_obj.update(file.read())

    return hash_obj.digest()


def find_duplicates(paths):
    file_list = list()
    print('Retrieving all files recursively...')
    for path in paths:
        for dirpath, dirname, filenames in os.walk(path):
            for name in filenames:
                if name.endswith(('mp4', 'png', 'jpeg', 'mkv', 'jpg', 'flv')):
                    file_list.append(os.path.join(dirpath, name))

        # Create dict of each file size with a list of files having that size
        size_dict = defaultdict(list)
        print('Getting file sizes...')
        for file_path in file_list:
            try:
                file_size = os.path.getsize(os.path.realpath(file_path))
                size_dict[file_size].append(file_path)
            except OSError:
                print('Unable to access file: ' + file_path)
                continue

        small_hash_dict = defaultdict(list)
        print('Checking first 1024 bytes...')
        counter = 0
        for size, file_list in size_dict.items():
            if len(file_list) < 2:
                continue

            for file_path in file_list:
                counter += 1
                try:
                    chunk_hash = get_hash(file_path, first_chunk=True)
                    small_hash_dict[(chunk_hash, size)].append(file_path)
                except OSError:
                    print('Unable to access file: ' + file_path)
                    continue
        print('{} files with identical sizes'.format(counter))

        for (_, _), file_list in small_hash_dict.items():
            if len(file_list) < 2:
                continue

            print('\nPotential duplicates found:')
            for file_path in file_list:
                print(os.path.relpath(file_path, start=path))

        hash_dict = dict()
        print('Calculating full hashes...')
        for (_, _), file_list in small_hash_dict.items():
            if len(file_list) < 2:
                continue

            for file_path in file_list:
                try:
                    full_hash = get_hash(file_path)
                    if full_hash in hash_dict.keys():
                        file_path = os.path.relpath(file_path, start=path)
                        duplicate = os.path.relpath(hash_dict[full_hash], start=path)
                        print('Duplicate found: {} and {}'.format(file_path, duplicate))
                    else:
                        hash_dict[full_hash] = file_path
                except OSError:
                    print('Unable to access file: ' + file_path)
                    continue


if __name__ == "__main__":
    if sys.argv[1:]:
        find_duplicates(sys.argv[1:])
