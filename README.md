# Patch Dataset

The Patch Dataset contains datapoints of kernel patches. Each datapoint includes the original kernel patch file, relevant bitcode files, and a tag indicating the type of error the patch is intended to fix.

## Components of a datapoint

1. The original kernel patch file, including the commit message.
2. Bitcode files that are relevant to the patch. Typically, only the files in the same directory as the patched files are necessary.
3. The patch's tag, which identifies the correctness of the patch.

To verify the correctness of a kernel patch, generate the corresponding bitcodes and access the patch's tag.

## Manual datapoint building instructions

### Build the Compiler

To build the compiler, run the following commands in the terminal:

```bash
git clone https://github.com/cla7aye15I4nd/llvm-project.git
cd llvm-project
mkdir build && cd build
cmake -DLLVM_ENABLE_PROJECTS=clang -DCMAKE_BUILD_TYPE=Release  -G "Unix Makefiles" ../llvm
make -j`nproc`
```

### Generate the Bitcode

To generate the bitcode, follow these instructions:

```bash
git clone https://github.com/torvalds/linux.git
cd linux
git checkout `patch_commit_id`
make CC=$HOME/llvm-project/build/bin/clang defconfig
make CC=$HOME/llvm-project/build/bin/clang -j`nproc`
```

### Datapoint Format

Create a new directory named `<commit id>` and put the following files in it:

- `patch.diff`: the original patch file.
- `patch.json`: the patch's metadata.
- `before`: the bitcodes of the file before the patch is applied.
- `after`: the bitcodes of the file after the patch is applied.

### Automate datapoint generation with `make-datapoint.py`

Use the `make-datapoint.py` script to automatically generate a patch datapoint. The script follows these steps to generate the kernel configuration file at `linux/.config` first:

1. Combine `defconfig`'s Kernel Hacking part and the other parts of `allyesconfig`. The goal is to enable all the options without enabling the Kernel Hacking part because sanitizer and debug are included in the Kernel Hacking part.
2. Disable device tree (`CONFIG_OF*` and `CONFIG_DCT`) because device tree is not supported by the current version of Clang.

If the script generates all modified files' bitcodes successfully, it generates a patch datapoint. Otherwise, it prints the error message and exits.

```bash
mkdir data # create a directory to store the datapoints
git clone https://github.com/torvalds/linux.git
python3 make-datapoint.py --help
```

### Collecting datapoints

Run `collect-datapoint.py` to collect the datapoints, it will identify the complete datapoints and move them to the `meta` directory.

```bash
mkdir meta
python3 collect-datapoint.py
```