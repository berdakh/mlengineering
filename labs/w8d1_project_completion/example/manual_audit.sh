#!/usr/bin/env bash
# Worked example (w8d1): a clean-clone audit done by hand, on a tiny SYNTHETIC project whose data file
# is git-ignored. It works in the author's working tree and fails in a clean clone; committing the data
# (or a download step with a hash) fixes it.
#
#   bash labs/w8d1_project_completion/example/manual_audit.sh
set -euo pipefail
WORK=$(mktemp -d)
trap 'rm -rf "$WORK"' EXIT
GIT=(git -c user.name=demo -c user.email=demo@example.invalid)

echo "== 1. the author's project (data/ is git-ignored)"
mkdir -p "$WORK/author/data" && cd "$WORK/author"
printf 'value\n3\n4\n5\n' > data/values.csv
cat > summarise.py <<'PY'
import json, pathlib
values = [float(v) for v in pathlib.Path("data/values.csv").read_text().split()[1:]]
pathlib.Path("results.json").write_text(json.dumps({"mean": sum(values) / len(values)}))
print("mean =", sum(values) / len(values))
PY
printf 'data/\nresults.json\n' > .gitignore
"${GIT[@]}" init -q && "${GIT[@]}" add -A && "${GIT[@]}" commit -qm "summarise values"
python summarise.py
echo "tracked files: $(git ls-files | tr '\n' ' ')"

echo "== 2. clean clone + fresh venv, run the same command"
"${GIT[@]}" clone -q "$WORK/author" "$WORK/clone"
python -m venv --without-pip "$WORK/venv"
cd "$WORK/clone"
if "$WORK/venv/bin/python" summarise.py 2>"$WORK/err.txt"; then echo "reproduced"; else
  echo "FAILED in the clone: $(tail -1 "$WORK/err.txt")"; fi

echo "== 3. fix: commit the (small) data file, then audit again"
cd "$WORK/author"
printf 'results.json\n' > .gitignore
"${GIT[@]}" add -A && "${GIT[@]}" commit -qm "commit the input data"
rm -rf "$WORK/clone" && "${GIT[@]}" clone -q "$WORK/author" "$WORK/clone" && cd "$WORK/clone"
"$WORK/venv/bin/python" summarise.py
diff <(python -c "import json;print(json.load(open('$WORK/author/results.json'))['mean'])") \
     <(python -c "import json;print(json.load(open('results.json'))['mean'])") && echo "author and clone agree"
