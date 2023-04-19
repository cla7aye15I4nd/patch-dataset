# Patch Dataset

A datapoint of a kernel patch comprises the following components:

- The original kernel patch file, which should include the commit message.
- Bitcode files that are relevant to the patch. Typically, we only need to consider the files located in the same directory as the patched files.
- The patch's tag, which is used to indicate the type of error that the patch is intended to fix.

To verify the accuracy of a kernel patch, it is necessary to generate the bitcodes that correspond to the patch, as well as to have access to the patch's tag. The tag serves as an identifier of the correctness of the patch.

## How to manually build a patch datapoint?

### Build the compiler

```bash
git clone https://github.com/cla7aye15I4nd/llvm-project.git
cd llvm-project
mkdir build && cd build
cmake -DLLVM_ENABLE_PROJECTS=clang -DCMAKE_BUILD_TYPE=Release  -G "Unix Makefiles" ../llvm
make -j`nproc`
```
### Generate the bitcode
```bash
git clone https://github.com/torvalds/linux.git
cd linux
git checkout `patch_commit_id`
make CC=$HOME/llvm-project/build/bin/clang defconfig
make CC=$HOME/llvm-project/build/bin/clang -j`nproc`
```

### Datapoint Format
Make a new directory named `<commit id>` and put the following files in it:

- `patch.diff`: the original patch file.
- `patch.json`: the patch's metadata.
- `before`: the bitcodes of the file before the patch is applied.
- `after`: the bitcodes of the file after the patch is applied.
- `kernel.patch`: the kernel patch file.

### make-datapoint.py

The `make-datapoint.py` script can be used to automatically generate a patch datapoint. The script follows the following steps to generate the kernel configuration file at `linux/.config`:

1. Combine `defconfig`'s Kernel Hacking part and the other parts of `allyesconfig`, the goal is to enable all the options but not enable the Kernel Hacking part because sanitizer and debug are included in the Kernel Hacking part.
2. Disable device tree (`CONFIG_OF*` and `CONFIG_DCT`), because device tree is not supported by the current version of Clang.

If the script find that all modified files' bitcodes are generated successfully, it will generate a patch datapoint. Otherwise, it will print the error message and exit.