#!/usr/bin/env python

import argparse
import os
import multiprocessing
import pathlib
import requests
import sys
import subprocess
import unidiff
import json

parser = argparse.ArgumentParser(
    prog='DataPoint Maker',
    description='Create a datapoint for the Linux kernel'
)

base_dir = os.path.dirname(os.path.realpath(__file__))

parser.add_argument('commit_id', nargs='?', help='Commit ID of the patch')
parser.add_argument('--file', help='File containing the patch list')
parser.add_argument('--linux-dir',
                    default=os.path.join(base_dir, 'linux'),
                    help='Path to the Linux kernel directory')
parser.add_argument('--data-dir',
                    default=os.path.join(base_dir, 'data'),
                    help='Path to the data directory')
parser.add_argument('--error-file',
                    default=os.path.join(base_dir, 'err.log'),
                    help='Path to the error log file')
parser.add_argument('--skip-compile',
                    help='Skip the compilation step', action='store_true')
parser.add_argument('--rebuild-all',
                    help='Rebuild the Linux kernel', action='store_true')
parser.add_argument('--rebuild-fail',
                    help='Rebuild the Linux kernel', action='store_true')

args = parser.parse_args()

def eprint(*_args, **kwargs):
    with open(args.error_file, 'a') as f:
        print(*_args, file=f, **kwargs)

def main():
    print('[+] DataPoint Maker')
    print('[+] Linux directory: %s' % args.linux_dir)
    print('[+] Data directory: %s' % args.data_dir)
    clear_linux()

    with open(args.error_file, 'w') as f:
        f.write('')
    
    if args.file:
        print('[+] Reading patch list from %s' % args.file)
        with open(args.file, 'r') as f:
            commit_set = list(dict.fromkeys(f.read().splitlines()))
            print('[+] Patch Number: %d' % len(commit_set))
            for commit_id in commit_set:
                create_datapoint(commit_id)
    else:
        commit_id = args.commit_id
        create_datapoint(commit_id)

def create_datapoint(commit_id):
    patch_text = check_patch(commit_id)

    # Create the patch directory
    commit_dir = os.path.join(args.data_dir, commit_id)
    patch_file = os.path.join(commit_dir, 'patch.diff')
    patch_json = os.path.join(commit_dir, 'patch.json')
    before_folder = os.path.join(commit_dir, 'before')
    after_folder = os.path.join(commit_dir, 'after')

    if os.path.exists(patch_json) and not args.rebuild_all:
        print('[+] Patch %s already exists' % commit_id)
        return
    
    if os.path.exists(patch_file) and not args.rebuild_fail and not args.rebuild_all:
        print('[+] Patch %s already exists' % commit_id)
        return

    parent_id, modified_files, affected_files = get_affected_files(commit_id, patch_text)

    if not modified_files:
        return

    if not os.path.exists(commit_dir):
        os.mkdir(commit_dir)
    if not os.path.exists(before_folder):
        os.mkdir(before_folder)
    if not os.path.exists(after_folder):
        os.mkdir(after_folder)

    with open(patch_file, 'w') as f:
        f.write(patch_text)

    for folder in affected_files.keys():
        bitcode_before_folder = os.path.join(before_folder, folder)
        bitcode_after_folder = os.path.join(after_folder, folder)
        if not os.path.exists(bitcode_before_folder):
            os.makedirs(bitcode_before_folder)
        if not os.path.exists(bitcode_after_folder):
            os.makedirs(bitcode_after_folder)

    switch_commit(commit_id)
    after_fail = compile_linux(affected_files, modified_files, after_folder)
    eprint(f'[{commit_id}] {after_fail}')

    if len(after_fail) == 0:
        switch_commit(parent_id)
        compile_linux(affected_files, modified_files, before_folder)

        with open(patch_json, 'w') as f:
            info = {
                'commit': commit_id,
                'parent': parent_id,
                'files': affected_files
            }
            json.dump(info, f, indent=4)


def switch_commit(commit_id):
    clear_linux()
    os.chdir(args.linux_dir)
    os.system(f'git checkout {commit_id}')
    os.chdir(base_dir)

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
    modified_files = []
    for file in patch:
        if file.path.endswith('.c'):
            modified_files.append(file.path)
        modified_folders.add(os.path.dirname(file.path))

    # Checkout commit
    print('[+] Checking out commit %s' % commit_id)
    os.chdir(args.linux_dir)
    os.system(f'git checkout {commit_id}')

    with os.popen(f'git show {commit_id}^ | head -n 1') as cmd:
        parent_id = cmd.read().strip().split()[1]

    print('[+] Modified folders: %s' % modified_folders)

    affected_files = {}
    for folder in modified_folders:
        files = []
        for file in os.listdir(os.path.join(args.linux_dir, folder)):
            if file.endswith('.c'):
                files.append(file)

        affected_files[folder] = files
        print('[+] Files from %s: %s' % (folder, files))

    return parent_id, modified_files, affected_files


def compile_linux(affected_files, modified_files, target_folder):
    """ Compile the Linux kernel """
    if args.skip_compile:
        return

    clear_linux()

    os.chdir(args.linux_dir)

    spliter = '# Kernel hacking'
    os.system(
        f'make CC={pathlib.Path.home()}/llvm-project/build/bin/clang defconfig')

    with open('.config', 'r') as f:
        kernel_hacking = f.read().split(spliter)[1]

    os.system(
        f'make CC={pathlib.Path.home()}/llvm-project/build/bin/clang allyesconfig')

    with open('.config', 'r') as f:
        config = f.read().split(spliter)[0] + spliter + kernel_hacking
        config = config.replace('CONFIG_DTC=y', '# CONFIG_DTC=y')
        config = config.replace('CONFIG_OF', '# CONFIG_OF')
    with open('.config', 'w') as f:
        f.write(config)

    # make CC=$HOME/llvm-project/build/bin/clang -j`nproc`
    nproc = multiprocessing.cpu_count() // 2

    print('[+] Compiling Linux kernel')
    target = []
    for folder, files in affected_files.items():
        for file in files:
            cname = os.path.join(folder, file)
            if cname.endswith('.c'):
                oname = cname.replace('.c', '.o')
                target.append(oname)
    
    os.system(f"yes '' | make CC={pathlib.Path.home()}/llvm-project/build/bin/clang oldconfig")

    cmd = f'make CC={pathlib.Path.home()}/llvm-project/build/bin/clang -j{nproc} {" ".join(target)}'

    compile_times = 0
    while compile_times < 2:
        print(f'[{compile_times}] Compiling Linux kernel')
        p = subprocess.Popen([cmd], stdout=subprocess.PIPE, stderr=subprocess.PIPE, shell=True, text=True)
        try:
            out, err = p.communicate(timeout=len(target)*5)
        except KeyboardInterrupt:
            p.kill()
            out, err = p.communicate(timeout=10)

        fail = []
        for folder, files in affected_files.items():
            for file in files:
                if os.path.exists(os.path.join(args.linux_dir, folder, file + '.bc')):
                    os.system(
                        f'cp {os.path.join(args.linux_dir, folder, file + ".bc")} {os.path.join(target_folder, folder)}')

        for file in modified_files:
            if not os.path.exists(os.path.join(target_folder, file + '.bc')):
                fail.append(file)

        if len(fail) == 0:
            break

        compile_times += 1

        print('X'*100)
        print(err)
        print('Y'*100)
        if "implicit declaration of function 'asm_volatile_goto'" in err:
            linux_patch = os.path.join(base_dir, 'config', 'asm_volatile_goto.patch')
            print('Try to apply patch %s' % linux_patch)
            os.system(f'patch -p1 < {linux_patch}')
            print('Try to compile again')
            continue
        if '#error New address family defined, please update secclass_map' in err:
            linux_patch = os.path.join(base_dir, 'config', 'secclass_map.patch')
            print('Try to apply patch %s' % linux_patch)
            os.system(f'patch -p1 < {linux_patch}')
            print('Try to compile again')
            continue

        break # do not have any solution
            
            
    os.chdir(base_dir)
    return fail


def clear_linux():
    os.chdir(args.linux_dir)
    os.system('make clean')
    os.system('git checkout .')
    os.system('git clean -xdf')
    os.system('git stash')
    os.chdir(base_dir)


if __name__ == '__main__':
    sys.exit(main())
