#!/bin/bash
cd "$(dirname "$0")" || exit 1
export PYTHONUTF8=1
WORKFLOW_PYTHON=""
for candidate in python3 python3.13 python3.12 python3.11; do
 if command -v "$candidate" >/dev/null 2>&1 && "$candidate" -c 'import sys; assert sys.version_info >= (3,9)' >/dev/null 2>&1; then WORKFLOW_PYTHON="$candidate"; break; fi
done
if [ -z "$WORKFLOW_PYTHON" ]; then echo "请先安装 Python 3.11 或更新版本：https://www.python.org/downloads/macos/"; read -r -p "按回车关闭"; exit 2; fi
"$WORKFLOW_PYTHON" -X utf8 scripts/portable.py menu
read -r -p "按回车关闭"
