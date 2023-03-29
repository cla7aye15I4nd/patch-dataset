#!/usr/bin/env python

import os
import requests
import sys
import unidiff

base_dir = os.path.dirname(os.path.realpath(__file__))

patch_dir = os.path.join(base_dir, 'data')
linux_dir = os.path.join(base_dir, 'linux')

def main():
    if len(sys.argv) < 2:
        print('Usage: %s <patch commit id>' % sys.argv[0])
        return 1

    if not os.path.exists(linux_dir):
        print('[-] Linux source code not found')
        return 1

    commit_id = sys.argv[1]

    patch_text = check_patch(commit_id)

    # Create the patch directory
    commit_dir = os.path.join(patch_dir, commit_id)
    patch_file = os.path.join(commit_dir, f'{commit_id}.diff')
    before_folder = os.path.join(commit_dir, 'before')
    after_folder = os.path.join(commit_dir, 'after')

    if not os.path.exists(commit_dir):
        os.mkdir(commit_dir)
    if not os.path.exists(before_folder):
        os.mkdir(before_folder)
    if not os.path.exists(after_folder):
        os.mkdir(after_folder)

    with open(patch_file, 'w') as f:
        f.write(patch_text)

    affected_files = get_affected_files(commit_id, patch_text)

    for folder in affected_files.keys():
        bitcode_folder = os.path.join(after_folder, folder)
        if not os.path.exists(bitcode_folder):
            os.makedirs(bitcode_folder)

def check_patch(commit_id):
    print('[+] Checking patch %s' % commit_id)

    # Download the patch 
    url = f'https://git.kernel.org/pub/scm/linux/kernel/git/torvalds/linux.git/patch/?id={commit_id}'
    r = requests.get(url)
    if r.status_code != 200:
        print('[-] Failed to download patch')
        sys.exit(1)
    
    patch_text = r.text
    r.close()

    return patch_text    

def get_affected_files(commit_id, patch_text):
    """ Analyze the which files need to be compiled """
    patch = unidiff.PatchSet(patch_text.splitlines())

    modified_folders = set()
    for file in patch:
        print('[+] Modified file %s' % file.path)
        modified_folders.add(os.path.dirname(file.path))

    # Checkout commit
    print('[+] Checking out commit %s' % commit_id)
    os.chdir(linux_dir)
    os.system(f'git checkout {commit_id}')
    
    print('[+] Modified folders: %s' % modified_folders)

    affected_files = {}
    for folder in modified_folders:
        files = []
        for file in os.listdir(os.path.join(linux_dir, folder)):
            if file.endswith('.c'):
                files.append(file)

        affected_files[folder] = files
        print('[+] Files from %s: %s' % (folder, files))
    
    return affected_files

if __name__ == '__main__':
    sys.exit(main()) 