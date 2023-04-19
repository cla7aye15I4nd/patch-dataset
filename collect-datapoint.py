import os

base_dir = os.path.dirname(os.path.realpath(__file__))
data_dir = os.path.join(base_dir, 'data')
meta_dir = os.path.join(base_dir, 'meta')

total = 0
for commit_id in os.listdir(data_dir):
  commit_path = os.path.join(data_dir, commit_id)
  if os.path.isdir(commit_path):
    if os.path.exists(os.path.join(commit_path, 'patch.json')):
      os.system(f'cp -r {commit_path} {meta_dir}')
      total += 1

print(f'Total: {total}')
