#!/usr/bin/env python3
"""Repair generated TB2.1 full89 verifier files for offline runtime closure.

Default mode is dry-run. With --execute, this edits the generated dataset only:
- run-tests.sh: remove the uvx resolver branch and call python3 -m pytest directly.
- docker-compose.yaml: remove public proxy/index/UV/PIP resolver environment lines.
- bn-fit-modify/solution.sh: replace network R package install with an offline package check.

A backup JSON with before/after sha256 hashes is written for every run.
"""

from __future__ import annotations

import argparse
import datetime as _dt
import hashlib
import json
import os
from pathlib import Path
from typing import Iterable

DEFAULT_DATASET = Path(
    "/mnt/shared-storage-user/mineru2-shared/zengweijun/nips2026/shared_bench/terminal-bench-2.1-yaml-full89-20260629"
)
DEFAULT_BACKUP_DIR = Path("_coordination/20260625_harbor_bench/artifacts")
EXPECTED_TASKS = 89

UVX_BLOCK = """if command -v uvx >/dev/null 2>&1; then\n  uvx -p 3.13 -w pytest==8.4.1 -w pytest-json-ctrf==0.3.5 \\\n    pytest --ctrf /logs/verifier/ctrf.json /tests/test_outputs.py -rA\nelse\n  python -m pytest --ctrf /logs/verifier/ctrf.json /tests/test_outputs.py -rA\nfi\n"""
PYTEST_LINE = "python3 -m pytest --ctrf /logs/verifier/ctrf.json /tests/test_outputs.py -rA\n"
CODE_FROM_IMAGE_PYTEST_LINE = "cd /tests && python3 -m pytest --ctrf /logs/verifier/ctrf.json /tests/test_outputs.py -rA\n"
CANCEL_ASYNC_PYTEST_LINE = "cp /tests/test.py /app/test.py\n" + PYTEST_LINE
BN_FIT_INSTALL_LINE = "R -e 'if (!require(\"remotes\")) install.packages(\"remotes\"); remotes::install_version(\"remotes\", version = \"2.5.0\"); remotes::install_version(\"bnlearn\", version = \"4.9\")'\n"
BN_FIT_OFFLINE_CHECK_LINE = "R -e 'stopifnot(requireNamespace(\"bnlearn\", quietly = TRUE))'\n"
MCMC_INSTALL_START = 'echo "=== DEBUG: Installing system dependencies ==="'
MCMC_MODEL_START = '# Create the Stan model file'
MCMC_OFFLINE_CHECK_BLOCK = '''echo "=== DEBUG: Verifying offline RStan runtime closure ==="
R -e "
stopifnot(requireNamespace('rstan', quietly = TRUE))
library(rstan)
rstan::rstan_options(auto_write = TRUE)
options(mc.cores = parallel::detectCores())
cat('RStan offline verification complete\\n')
"

'''

COBOL_INSTALL_LINE = "apt-get update && apt-get install -y gnucobol3\n"
COBOL_OFFLINE_CHECK_LINE = "command -v cobc >/dev/null\n"
MERGE_DIFF_GIT_INSTALL_BLOCK = """# Install git
apt-get update
apt-get install -y git
"""
MERGE_DIFF_GIT_OFFLINE_CHECK_BLOCK = """# Verify git is already baked into the offline image
command -v git >/dev/null
"""
LOG_SUMMARY_INSTALL_LINE = "apt-get update && apt-get install -y grep coreutils\n"
LOG_SUMMARY_OFFLINE_CHECK_BLOCK = """command -v grep >/dev/null
command -v date >/dev/null
command -v sort >/dev/null
"""

KV_STORE_GRPC_INSTALL_LINE = "pip install grpcio==1.73.0 grpcio-tools==1.73.0\n"
KV_STORE_GRPC_OFFLINE_CHECK_BLOCK = """python - <<'PY'
import grpc
import grpc_tools.protoc
PY
"""
LARGEST_EIGEN_INSTALL_LINE = "pip install eigenpy==3.10.3\n"
LARGEST_EIGEN_OFFLINE_CHECK_BLOCK = """python - <<'PY'
import eigenpy
PY
"""
RAMAN_FITTING_INSTALL_LINE = "pip install scipy==1.16.0 numpy==2.3.1\n"
RAMAN_FITTING_OFFLINE_CHECK_BLOCK = """python - <<'PY'
import numpy
import scipy
PY
"""

ADAPTIVE_OPENSSL_INSTALL_BLOCK = """apt-get update
apt-get install -y openssl
"""
ADAPTIVE_OPENSSL_OFFLINE_CHECK_BLOCK = """command -v openssl >/dev/null
"""
ADAPTIVE_R_INSTALL_START = '# Install R and required packages'
ADAPTIVE_VALIDATION_START = "# Add input validation to the ars function if it\'s missing"
ADAPTIVE_R_OFFLINE_CHECK_BLOCK = """# Verify R is baked into the offline image
echo "Checking for R installation..."
command -v Rscript >/dev/null
Rscript --version

"""
OVERFULL_INSTALL_BLOCK = """export DEBIAN_FRONTEND=noninteractive
apt update
apt install -y python3-pip
"""
OVERFULL_OFFLINE_CHECK_BLOCK = """command -v python3 >/dev/null
"""

CRACK_LZMA_INSTALL_BLOCK = """apt-get update
apt-get install libcompress-raw-lzma-perl
"""
CRACK_LZMA_INSTALL_BLOCK_TRAILING = """apt-get update
apt-get install libcompress-raw-lzma-perl 
"""
CRACK_LZMA_OFFLINE_CHECK_BLOCK = """perl -MCompress::Raw::Lzma -e 'print qq(lzma-ok\\n)'
"""
CRACK_7ZIP_INSTALL_LINE = "apt-get install 7zip\n"
CRACK_7ZIP_OFFLINE_CHECK_LINE = "command -v 7z >/dev/null || command -v 7zz >/dev/null\n"
DNA_INSTALL_BLOCK = """apt-get update
apt-get install -y emboss primer3
"""
DNA_OFFLINE_CHECK_BLOCK = """command -v primer3_core >/dev/null
command -v needle >/dev/null || command -v water >/dev/null || command -v seqret >/dev/null
"""
FINANCIAL_TESSERACT_INSTALL_LINE = "apt-get update && apt-get install -y tesseract-ocr\n"
FINANCIAL_TESSERACT_OFFLINE_CHECK_LINE = "command -v tesseract >/dev/null\n"
FINANCIAL_UV_RUN_LINE = "uv run document_processor.py\n"
FINANCIAL_PYTHON_RUN_LINE = "python3 document_processor.py\n"

SQLITE_FOSSIL_INSTALL_BLOCK = 'apt-get update\napt-get install -y fossil\n'
SQLITE_FOSSIL_OFFLINE_CHECK_BLOCK = 'command -v fossil >/dev/null\n'
SQLITE_TZDATA_INSTALL_LINE = 'DEBIAN_FRONTEND=noninteractive apt-get -y install tzdata\n'
SQLITE_TZDATA_OFFLINE_CHECK_LINE = 'test -f /usr/share/zoneinfo/UTC\n'
SQLITE_BUILD_INSTALL_LINE = 'apt-get install -y gcc jimsh tclsh make\n'
SQLITE_BUILD_OFFLINE_CHECK_BLOCK = 'command -v gcc >/dev/null\ncommand -v jimsh >/dev/null\ncommand -v tclsh >/dev/null\ncommand -v make >/dev/null\n'


NGINX_INSTALL_LINE = "apt-get update && apt-get install -y nginx\n"
NGINX_OFFLINE_CHECK_LINE = "command -v nginx >/dev/null\n"
NGINX_LOCAL_CURL_LINE = 'curl -s http://localhost:8080 || echo "Server is not responding on port 8080"\n'
NGINX_LOCAL_STATUS_LINE = 'pgrep nginx >/dev/null || echo "Server is not responding on port 8080"\n'
CONFIGURE_GIT_WEBSERVER_INSTALL_BLOCK = """DEBIAN_FRONTEND=noninteractive apt-get update
DEBIAN_FRONTEND=noninteractive apt-get install -y git nginx openssh-server
"""
CONFIGURE_GIT_WEBSERVER_OFFLINE_CHECK_BLOCK = """command -v git >/dev/null
command -v nginx >/dev/null
command -v sshd >/dev/null
"""
PMARS_SETUP_START = "# Enable deb-src for stable"
PMARS_BUILD_START = "# Build curses (headless) version"
PMARS_OFFLINE_CHECK_BLOCK = """# Verify pMARS source and build dependencies are already baked into the offline image
command -v gcc >/dev/null
command -v make >/dev/null
test -d /app/pmars-*/src

"""

PYPI_APT_INSTALL_BLOCK = """DEBIAN_FRONTEND=noninteractive apt-get update
DEBIAN_FRONTEND=noninteractive apt-get install -y python3 python3-pip python3-venv apache2-utils
"""
PYPI_APT_OFFLINE_CHECK_BLOCK = """command -v python3 >/dev/null
command -v htpasswd >/dev/null
"""
PYPI_VENV_INSTALL_BLOCK = """# Create a Python virtual environment to keep dependencies isolated
python3 -m venv /opt/pypiserver/venv

# Install pypiserver and passlib with pinned versions for reproducibility
/opt/pypiserver/venv/bin/pip install pypiserver==2.3.2 passlib[bcrypt]==1.7.4 bcrypt==4.3.0 packaging==25.0
"""
PYPI_VENV_OFFLINE_CHECK_BLOCK = """# Verify pypiserver dependencies are already baked into the offline image
command -v pypi-server >/dev/null
python3 - <<'PY'
import pypiserver, passlib, bcrypt, packaging
PY
"""
PYPI_SYSTEM_BUILD_INSTALL_LINE = "python3 -m pip install build==1.3.0 twine==6.1.0\n"
PYPI_BUILD_OFFLINE_CHECK_BLOCK = """command -v twine >/dev/null
python3 - <<'PY'
import build, twine
PY
"""
PYPI_RUNTIME_BUILD_INSTALL_LINE = "pip install build==1.3.0 twine==6.1.0\n"
PYPI_SERVER_VENV_CMD = "nohup /opt/pypiserver/venv/bin/pypi-server \\\n"
PYPI_SERVER_BAKED_CMD = "nohup pypi-server \\\n"

CHESS_STOCKFISH_INSTALL_LINE = "apt install -y stockfish\n"
CHESS_STOCKFISH_OFFLINE_CHECK_LINE = "test -x /usr/games/stockfish\n"
CHESS_PIP_INSTALL_LINE = "pip3 install numpy==2.3.2 python-chess==1.2.0 --break-system-packages\n"
CHESS_PYTHON_OFFLINE_CHECK_BLOCK = """/usr/bin/python3 - <<'PY'
import numpy, chess, PIL
PY
"""
CHESS_RUN_LINE = "python3 solve.py\n"
CHESS_RUN_BAKED_LINE = "/usr/bin/python3 solve.py\n"
CUSTOM_MEMORY_ULIMIT_LINE = "ulimit -c unlimited\n"
CUSTOM_MEMORY_ULIMIT_OFFLINE_LINE = "ulimit -c unlimited || true\n"


GCODE_SETUP_BLOCK = """apt-get update -y
apt-get install -y python3-opencv
pip install matplotlib==3.10.7 pytesseract==0.3.13 pillow==12.0.0 opencv-python==4.12.0.88


# echo "Python package versions:"
# pip freeze | grep -E "matplotlib|pytesseract|pillow|opencv-python"

# echo -e "\nSystem package versions:"
# dpkg -l | grep -E "tesseract-ocr|libtesseract-dev" | awk '{print $2 "\t" $3}'

apt install -y tesseract-ocr libtesseract-dev
"""
GCODE_OFFLINE_CHECK_BLOCK = """command -v tesseract >/dev/null
python3 - <<'PY'
import cv2, matplotlib, numpy, pytesseract
from PIL import Image
PY

"""
GCODE_RUN_LINES = (
    ("python3 makeseg.py\n", "python3 makeseg.py\n"),
    ("python3 render.py 0 201 0\n", "python3 render.py 0 201 0\n"),
    ("python3 ocr.py\n", "python3 ocr.py\n"),
)

PYTORCH_MODEL_CLI_PIP_START = "# Install Torch, specifically version 2.7.0"
PYTORCH_MODEL_CLI_WEIGHT_START = "# Check the weights in the .pth file"
PYTORCH_MODEL_CLI_PYTHON_OFFLINE_CHECK_BLOCK = """python3 - <<'PY'
import torch, numpy
PY

"""
PYTORCH_MODEL_CLI_GCC_START = "# Install GCC"
PYTORCH_MODEL_CLI_C_FILE_START = "# Create the C file"
PYTORCH_MODEL_CLI_GCC_OFFLINE_CHECK_BLOCK = """# Verify GCC is already baked into the offline image
command -v gcc >/dev/null

"""




POV_RAY_INSTALL_START = "# Install build tools and dependencies"
POV_RAY_CHECK_START = "which gcc ||"
POV_RAY_OFFLINE_CHECK_BLOCK = """# Verify build tools and POV-Ray 2.2 archives are already baked into the offline image
command -v gcc >/dev/null
command -v make >/dev/null
command -v uncompress >/dev/null
test -s /opt/tb21-vendor/povray-2.2-archives/POVDOC.TAR.Z
test -s /opt/tb21-vendor/povray-2.2-archives/POVSCN.TAR.Z
test -s /opt/tb21-vendor/povray-2.2-archives/POVSRC.TAR.Z

"""
POV_RAY_DOWNLOAD_START = "# Download POV-Ray 2.2 source archives"
POV_RAY_EXTRACT_START = "# Extract the archives"
POV_RAY_COPY_ARCHIVES_BLOCK = """# Copy baked POV-Ray 2.2 source archives
cp /opt/tb21-vendor/povray-2.2-archives/POVDOC.TAR.Z /app/POVDOC.TAR.Z
cp /opt/tb21-vendor/povray-2.2-archives/POVSCN.TAR.Z /app/POVSCN.TAR.Z
cp /opt/tb21-vendor/povray-2.2-archives/POVSRC.TAR.Z /app/POVSRC.TAR.Z

"""

MTEB_LEADERBOARD_READY_SUMMARIES = [
    Path(__file__).resolve().parents[1] / "_coordination/20260625_harbor_bench/artifacts/tb21_closure_full89_r2/mteb-leaderboard.json",
    Path(__file__).resolve().parents[1] / "_coordination/20260625_harbor_bench/artifacts/tb21_closure_full89_r1_v3/mteb-leaderboard.json",
]
MTEB_LEADERBOARD_CLONE_BLOCK = """git clone https://github.com/embeddings-benchmark/results
cd results
# Checkout to commit within August 2025
git checkout c0fd3271442f8c0c839084a109fede85c8514dab
"""
MTEB_LEADERBOARD_COPY_BLOCK = """rm -rf /app/results
cp -a /opt/tb21-vendor/mteb-results /app/results
cd results
test "$(cat .tb21_commit)" = c0fd3271442f8c0c839084a109fede85c8514dab
"""

INSTALL_WINDOWS_QEMU_SOURCE_START = "# Compile QEMU 5.2.0 from source for Windows 3.11 compatibility"
INSTALL_WINDOWS_IMAGE_CHECK_START = "# Ensure Windows 3.11 disk image exists"
INSTALL_WINDOWS_QEMU_OFFLINE_CHECK_BLOCK = """# Verify QEMU and Windows 3.11 image are already baked into the offline image
command -v qemu-system-i386 >/dev/null
test -x "${QEMU_BIN:-/usr/local/bin/qemu-system-i386}"
test -f "${WIN311_IMG:-/app/isos/win311.img}"

"""
INSTALL_WINDOWS_EXTERNAL_IP_WGET_LINE = "        EXTERNAL_IP=$(wget -qO- --timeout=5 \"$ip_service\" 2>/dev/null | head -1 | tr -d '\\n\\r ')\n"
INSTALL_WINDOWS_EXTERNAL_IP_LOCAL_LINE = '        EXTERNAL_IP="localhost"\n'
POV_RAY_WGET_CHECK_LINE = 'which wget || { echo "ERROR: wget not found"; exit 1; }\n'
SAM_CELL_SEG_CURL_CHECK_LINE = 'command -v curl >/dev/null\n'
TRAIN_FASTTEXT_INSTALL_LINE = "apt-get update && apt-get install -y git && apt-get install build-essential -y\n"
TRAIN_FASTTEXT_OFFLINE_CHECK_LINE = "command -v fasttext >/dev/null\n"
TRAIN_FASTTEXT_GIT_CLONE_LINE = "git clone https://github.com/facebookresearch/fastText.git\n"
TRAIN_FASTTEXT_COPY_BLOCK = """rm -rf /app/fastText
cp -a /opt/tb21-vendor/fastText /app/fastText
"""
TRAIN_FASTTEXT_BUILD_LINE = 'cd fastText && make && export PATH="/app/fastText:$PATH" && cd /app\n'
TRAIN_FASTTEXT_BUILD_OFFLINE_LINE = "cd /app\n"

COUNT_DATASET_TOKENS_PIP_LINE = "pip install datasets==4.0.0 transformers==4.56.0 jinja2==3.1.6\n"
COUNT_DATASET_TOKENS_OFFLINE_CHECK_BLOCK = """export HF_HUB_OFFLINE=1
export TRANSFORMERS_OFFLINE=1
export HF_DATASETS_OFFLINE=1
python3 - <<'PY'
import datasets, jinja2, transformers
PY
"""
COUNT_DATASET_TOKENS_IMPORT_LINE = "from datasets import load_dataset\n"
COUNT_DATASET_TOKENS_TOKENIZER_LINE = 'tokenizer = AutoTokenizer.from_pretrained("Qwen/Qwen2.5-1.5B-Instruct", trust_remote_code=True)\n'
COUNT_DATASET_TOKENS_TOKENIZER_OFFLINE_LINE = 'tokenizer = AutoTokenizer.from_pretrained("Qwen/Qwen2.5-1.5B-Instruct", trust_remote_code=True, local_files_only=True)\n'
COUNT_DATASET_TOKENS_DATASET_LINE = 'ds = load_dataset("ryanmarten/OpenThoughts-1k-sample", "metadata", split="train")\n'

MAKE_DOOM_FOR_MIPS_INSTALL_LINE = "apt-get update && apt install -y clang gcc-mips-linux-gnu g++-mips-linux-gnu llvm llvm-dev lld\n"
MAKE_DOOM_FOR_MIPS_OFFLINE_CHECK_BLOCK = """command -v clang >/dev/null
command -v mips-linux-gnu-as >/dev/null
command -v mips-linux-gnu-ld >/dev/null
command -v llc >/dev/null
"""

PROTEIN_ASSEMBLY_INSTALL_LINE = 'pip install biopython==1.85 rcsb-api==1.4.0 dnachisel==3.2.16 pandas==2.2.3 requests==2.32.4\n'
PROTEIN_ASSEMBLY_DISCOVERY_START = '# Search the pdb to determine the identity of the antibody binder.\n'
PROTEIN_ASSEMBLY_GBLOCK_START = "# Now let's search sequences.csv for a donor acceptor pair"
PROTEIN_ASSEMBLY_OFFLINE_CHECK_BLOCK = "# Verify biology Python packages and use the baked offline PDB/FPbase fixture\npython3 - <<'PY'\nimport Bio, dnachisel, pandas\nPY\ncp /opt/tb21-vendor/protein-assembly/sequences.csv sequences.csv\ncat sequences.csv\n\n"
RSTAN_PYSTAN_INSTALL_START = '# installation of pystan3 is tricky in the arm64 architecture. \n'
RSTAN_PYSTAN_SCRIPT_START = 'echo "=== Solution: PyStan script ==="\n'
RSTAN_PYSTAN_OFFLINE_CHECK_BLOCK = '# Verify baked PyStan runtime and activate it for the converted script\nexport VIRTUAL_ENV=/opt/py310\nexport PATH="$VIRTUAL_ENV/bin:$PATH"\npython - <<\'PY\'\nimport nest_asyncio, numpy, pandas, stan\nPY\n\n'
RSTAN_PYSTAN_RUNTIME_PIP_LINE = 'pip install "setuptools<71"\n'
COMPCERT_INSTALL_START = 'apt-get update\n'
COMPCERT_CC_VER_LINE = 'CC_VER=3.13.1\n'
COMPCERT_OFFLINE_CHECK_BLOCK = '# Verify baked Opam/Coq/Menhir toolchain and vendored CompCert source\ncommand -v opam >/dev/null\ncommand -v make >/dev/null\ncommand -v gcc >/dev/null\nexport OPAMYES=1 OPAMCOLOR=never OPAMJOBS=1\neval "$(opam env --switch=compcert-4.14)"\ncoqc -v\nmenhir --version\ntest -d /opt/tb21-vendor/CompCert/.git\n\n'
COMPCERT_GIT_CLONE_LINE = 'git clone --depth 1 --branch "$CC_TAG" https://github.com/AbsInt/CompCert.git "$SRC_DIR"\n'
COMPCERT_COPY_BLOCK = 'cp -a /opt/tb21-vendor/CompCert "$SRC_DIR"\n'
COMPCERT_MAKE_SERIAL_LINE = 'make -j1\n'
COMPCERT_MAKE_PARALLEL_BLOCK = '''COMPCERT_JOBS="${TB21_COMPCERT_JOBS:-}"
if [ -z "$COMPCERT_JOBS" ]; then
  COMPCERT_JOBS="$(nproc 2>/dev/null || echo 4)"
  if [ "$COMPCERT_JOBS" -gt 8 ]; then
    COMPCERT_JOBS=8
  fi
fi
make -j"$COMPCERT_JOBS"
'''

CAFFE_CIFAR_APT_START = 'apt-get update\n'
CAFFE_CIFAR_GIT_LINE = 'git clone https://github.com/BVLC/caffe.git\n'
CAFFE_CIFAR_INSTALL_END = CAFFE_CIFAR_GIT_LINE
CAFFE_CIFAR_OFFLINE_CHECK_BLOCK = '# Verify Caffe build dependencies and vendored source/data are baked into the offline image\ncommand -v cmake >/dev/null\ncommand -v make >/dev/null\ncommand -v protoc >/dev/null\ntest -d /opt/tb21-vendor/caffe/.git\ntest -f /opt/tb21-vendor/caffe/data/cifar10/data_batch_1.bin\ntest -f /opt/tb21-vendor/caffe/data/cifar10/test_batch.bin\n\n'
CAFFE_CIFAR_COPY_BLOCK = 'rm -rf caffe\ncp -a /opt/tb21-vendor/caffe caffe\n'
CAFFE_CIFAR_OPENCV4_INCLUDE_LINE = 'echo "INCLUDE_DIRS += /usr/include/opencv4" >> Makefile.config\n'
CAFFE_CIFAR_HDF5_CONFIG_BLOCK = '''echo "INCLUDE_DIRS += /usr/include/hdf5/serial" >> Makefile.config
echo "LIBRARY_DIRS += /usr/lib/x86_64-linux-gnu/hdf5/serial" >> Makefile.config
echo "LIBRARIES += hdf5_serial_hl hdf5_serial" >> Makefile.config
'''
CAFFE_CIFAR_OPENCV4_HEADER_PATCH_BLOCK = """grep -RIl 'opencv2/core/core.hpp\|opencv2/highgui/highgui.hpp\|opencv2/imgproc/imgproc.hpp' src include examples | xargs -r sed -i 's#opencv2/core/core.hpp#opencv2/core.hpp#g; s#opencv2/highgui/highgui.hpp#opencv2/highgui.hpp#g; s#opencv2/imgproc/imgproc.hpp#opencv2/imgproc.hpp#g'
grep -RIl 'CV_LOAD_IMAGE_COLOR\|CV_LOAD_IMAGE_GRAYSCALE' src include examples | xargs -r sed -i 's/CV_LOAD_IMAGE_COLOR/cv::IMREAD_COLOR/g; s/CV_LOAD_IMAGE_GRAYSCALE/cv::IMREAD_GRAYSCALE/g'
"""

SAM_CELL_SEG_INSTALL_START = "# I guess in theory you don't need to install these since you could write the script without\n"
SAM_CELL_SEG_SCRIPT_START = "#----------------------------------------------------------\ncat > convert_masks.py"
SAM_CELL_SEG_OFFLINE_CHECK_BLOCK = """# Verify MobileSAM runtime dependencies and weights are baked into the offline image
command -v git >/dev/null
command -v curl >/dev/null
python3 - <<'PYCODE'
import cv2, pandas, shapely, timm, torch, torchvision
from mobile_sam import SamPredictor, sam_model_registry
PYCODE
test -s /app/mobile_sam.pt

"""

BUILD_CYTHON_GIT_CLONE_LINE = "git clone --depth 1 --branch 0.5.3 https://github.com/SPOCKnots/pyknotid.git /app/pyknotid\n"
BUILD_CYTHON_COPY_BLOCK = """rm -rf /app/pyknotid
cp -a /opt/tb21-vendor/pyknotid /app/pyknotid

"""
BUILD_CYTHON_PIP_INSTALL_LINE = "pip install setuptools==80.9.0 cython==3.1.3\n"
BUILD_CYTHON_IMPORT_CHECK_BLOCK = """python3 - <<'PY'
import Cython, setuptools
PY
"""
BUILD_CYTHON_EDITABLE_INSTALL_LINE = "pip install -e .\n"
BUILD_CYTHON_PTH_BLOCK = """python3 - <<'PY'
from pathlib import Path
import site
for directory in site.getsitepackages():
    Path(directory, 'pyknotid-local.pth').write_text('/app/pyknotid\\n')
PY
"""

COMPOSE_ENV_PREFIXES = (
    "    - http_proxy=",
    "    - https_proxy=",
    "    - HTTP_PROXY=",
    "    - HTTPS_PROXY=",
    "    - no_proxy=",
    "    - NO_PROXY=",
    "    - UV_HTTP_TIMEOUT=",
    "    - UV_INDEX_URL=",
    "    - UV_DEFAULT_INDEX=",
    "    - PIP_INDEX_URL=",
    "    - PIP_DEFAULT_TIMEOUT=",
    "    - PIP_RETRIES=",
)

COMPOSE_CACHE_VOLUME_MARKERS = (
    "terminal_bench_huggingface:/root/.cache/huggingface",
    "terminal_bench_uv:/root/.cache/uv",
    "terminal_bench_qwen_nvm:/root/.nvm",
)

NETWORK_MARKERS = ("apt-get", "curl ", "wget ", "pip install", "uv pip install", "git clone", "npm install")
RUNTIME_MARKERS = ("uvx ", "uvx\t", " -w ", " --with ", "pytest==", "pytest-json-ctrf==")
COMPOSE_PUBLIC_MARKERS = (
    "UV_INDEX_URL=",
    "UV_DEFAULT_INDEX=",
    "PIP_INDEX_URL=",
    "http_proxy=",
    "https_proxy=",
    "HTTP_PROXY=",
    "HTTPS_PROXY=",
)
SOLUTION_NETWORK_MARKERS = ("install.packages", "install_version", "curl ", "wget ", "pip install", "apt-get", "uv run")
TEST_OUTPUT_NETWORK_MARKERS = ("apt-get", "apt install", "urllib.request.urlretrieve", "https://github.com/")
GIT_MULTIBRANCH_TEST_INSTALL_BLOCK = """apt-get update
DEBIAN_FRONTEND=noninteractive apt-get install -y curl expect git openssh-client
"""
GIT_MULTIBRANCH_TEST_OFFLINE_CHECK_BLOCK = """command -v curl >/dev/null
command -v expect >/dev/null
command -v git >/dev/null
command -v ssh >/dev/null
"""
FILTER_JS_GITHUB_URL_LINE = '    url = "https://github.com/davidwagner/html-sanitizer-testbed/archive/refs/heads/master.zip"\n'
FILTER_JS_URLRETRIEVE_LINE = "    urllib.request.urlretrieve(url, zip_path)\n"
FILTER_JS_LOCAL_ZIP_COPY_LINE = '    shutil.copyfile("/opt/tb21-vendor/filter-js-from-html/testbed.zip", zip_path)\n'
BUILD_CYTHON_TEST_GIT_CLONE_BLOCK = """        git_cmd = [
            "git",
            "clone",
            "--depth",
            "1",
            "--branch",
            "0.5.3",
            "https://github.com/SPOCKnots/pyknotid.git",
            temp_dir,
        ]
        result = subprocess.run(git_cmd, capture_output=True, text=True)
"""
BUILD_CYTHON_TEST_LOCAL_COPY_LINE = '        shutil.copytree("/app/pyknotid", temp_dir, dirs_exist_ok=True)\n'
OVERFULL_TEST_APT_REINSTALL_LINE = "    os.system('apt install -y --reinstall texlive-latex-base')\n"
OVERFULL_TEST_PDFLATEX_CHECK_LINE = '    assert os.system("command -v pdflatex >/dev/null") == 0\n'

def sha256(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def count_markers(paths: Iterable[Path], markers: tuple[str, ...]) -> tuple[int, list[str]]:
    return count_markers_in_texts(
        ((path, path.read_text(encoding="utf-8", errors="replace")) for path in paths),
        markers,
    )


def count_markers_in_texts(items: Iterable[tuple[Path, str]], markers: tuple[str, ...]) -> tuple[int, list[str]]:
    hits = 0
    samples: list[str] = []
    for path, text in items:
        for lineno, line in enumerate(text.splitlines(), 1):
            if any(marker in line for marker in markers):
                hits += 1
                if len(samples) < 12:
                    samples.append(f"{path.name}:{lineno}:{line.strip()}")
    return hits, samples


def offline_run_tests_text(task_id: str) -> str:
    if task_id == "code-from-image":
        pytest_cmd = CODE_FROM_IMAGE_PYTEST_LINE.rstrip("\n")
    elif task_id == "cancel-async-tasks":
        pytest_cmd = CANCEL_ASYNC_PYTEST_LINE.rstrip("\n")
    else:
        pytest_cmd = PYTEST_LINE.rstrip("\n")
    return f"""#!/bin/bash
set +e
mkdir -p /logs/verifier

# Check if we're in a valid working directory
if [ "$PWD" = "/" ]; then
    echo "Error: No working directory set. Please set a WORKDIR in your Dockerfile before running this script."
    exit 1
fi

{pytest_cmd}
rc=$?

if [ "$rc" -eq 0 ]; then
  echo 1 > /logs/verifier/reward.txt
else
  echo 0 > /logs/verifier/reward.txt
fi
exit "$rc"
"""


def repair_run_tests(path: Path, text: str) -> tuple[str, bool]:
    resolver_markers = (
        "apt-get update",
        "apt-get install",
        "curl -LsSf https://astral.sh/uv/",
        "source $HOME/.local/bin/env",
        "uvx",
        "pip install",
        "python -m pytest",
        "pytest==",
    )
    if any(marker in text for marker in resolver_markers):
        repaired = offline_run_tests_text(path.parent.name)
        return repaired, repaired != text
    if path.parent.name == "code-from-image" and PYTEST_LINE in text and CODE_FROM_IMAGE_PYTEST_LINE not in text:
        text = text.replace(PYTEST_LINE, CODE_FROM_IMAGE_PYTEST_LINE)
        return text, True
    if path.parent.name == "cancel-async-tasks" and PYTEST_LINE in text and CANCEL_ASYNC_PYTEST_LINE not in text:
        text = text.replace(PYTEST_LINE, CANCEL_ASYNC_PYTEST_LINE)
        return text, True
    return text, False


def repair_compose(text: str) -> tuple[str, int]:
    removed = 0
    kept: list[str] = []
    for line in text.splitlines(keepends=True):
        raw = line.rstrip("\n")
        normalized = raw.lstrip()
        if any(raw.startswith(prefix) for prefix in COMPOSE_ENV_PREFIXES) or any(
            normalized.startswith(prefix.strip()) for prefix in COMPOSE_ENV_PREFIXES
        ):
            removed += 1
            continue
        if any(marker in raw for marker in COMPOSE_CACHE_VOLUME_MARKERS):
            removed += 1
            continue
        kept.append(line)
    return "".join(kept), removed


def ensure_import(text: str, import_line: str, *, after: str) -> tuple[str, bool]:
    if import_line in text:
        return text, False
    if after in text:
        return text.replace(after, after + import_line, 1), True
    return import_line + text, True


def repair_test_outputs(path: Path, text: str) -> tuple[str, bool]:
    task_id = path.parent.parent.name
    changed = False
    if task_id == "git-multibranch":
        if GIT_MULTIBRANCH_TEST_INSTALL_BLOCK in text:
            text = text.replace(GIT_MULTIBRANCH_TEST_INSTALL_BLOCK, GIT_MULTIBRANCH_TEST_OFFLINE_CHECK_BLOCK, 1)
            changed = True
        return text, changed
    if task_id == "filter-js-from-html":
        if FILTER_JS_GITHUB_URL_LINE in text:
            text = text.replace(FILTER_JS_GITHUB_URL_LINE, "", 1)
            changed = True
        if FILTER_JS_URLRETRIEVE_LINE in text:
            text, _ = ensure_import(text, 'import shutil\n', after='import signal\n')
            text = text.replace(FILTER_JS_URLRETRIEVE_LINE, FILTER_JS_LOCAL_ZIP_COPY_LINE, 1)
            changed = True
        return text, changed
    if task_id == "build-cython-ext":
        if BUILD_CYTHON_TEST_GIT_CLONE_BLOCK in text:
            text, _ = ensure_import(text, 'import shutil\n', after='import os\n')
            text = text.replace(BUILD_CYTHON_TEST_GIT_CLONE_BLOCK, BUILD_CYTHON_TEST_LOCAL_COPY_LINE, 1)
            changed = True
        return text, changed
    if task_id == "overfull-hbox":
        if OVERFULL_TEST_APT_REINSTALL_LINE in text:
            text = text.replace(OVERFULL_TEST_APT_REINSTALL_LINE, OVERFULL_TEST_PDFLATEX_CHECK_LINE, 1)
            changed = True
        return text, changed
    return text, False
def repair_solution(path: Path, text: str) -> tuple[str, bool]:
    task_id = path.parent.name
    if task_id == "bn-fit-modify":
        if BN_FIT_INSTALL_LINE in text:
            return text.replace(BN_FIT_INSTALL_LINE, BN_FIT_OFFLINE_CHECK_LINE, 1), True
        return text, False
    if task_id == "mcmc-sampling-stan":
        start = text.find(MCMC_INSTALL_START)
        end = text.find(MCMC_MODEL_START)
        if start != -1 and end != -1 and start < end:
            return text[:start] + MCMC_OFFLINE_CHECK_BLOCK + text[end:], True
    if task_id == "cobol-modernization":
        if COBOL_INSTALL_LINE in text:
            return text.replace(COBOL_INSTALL_LINE, COBOL_OFFLINE_CHECK_LINE, 1), True
        return text, False
    if task_id == "merge-diff-arc-agi-task":
        if MERGE_DIFF_GIT_INSTALL_BLOCK in text:
            return text.replace(MERGE_DIFF_GIT_INSTALL_BLOCK, MERGE_DIFF_GIT_OFFLINE_CHECK_BLOCK, 1), True
        return text, False
    if task_id == "log-summary-date-ranges":
        if LOG_SUMMARY_INSTALL_LINE in text:
            return text.replace(LOG_SUMMARY_INSTALL_LINE, LOG_SUMMARY_OFFLINE_CHECK_BLOCK, 1), True
        return text, False
    if task_id == "kv-store-grpc":
        if KV_STORE_GRPC_INSTALL_LINE in text:
            return text.replace(KV_STORE_GRPC_INSTALL_LINE, KV_STORE_GRPC_OFFLINE_CHECK_BLOCK, 1), True
        return text, False
    if task_id == "largest-eigenval":
        if LARGEST_EIGEN_INSTALL_LINE in text:
            return text.replace(LARGEST_EIGEN_INSTALL_LINE, LARGEST_EIGEN_OFFLINE_CHECK_BLOCK, 1), True
        return text, False
    if task_id == "raman-fitting":
        if RAMAN_FITTING_INSTALL_LINE in text:
            return text.replace(RAMAN_FITTING_INSTALL_LINE, RAMAN_FITTING_OFFLINE_CHECK_BLOCK, 1), True
        return text, False
    if task_id == "adaptive-rejection-sampler":
        changed = False
        if ADAPTIVE_OPENSSL_INSTALL_BLOCK in text:
            text = text.replace(ADAPTIVE_OPENSSL_INSTALL_BLOCK, ADAPTIVE_OPENSSL_OFFLINE_CHECK_BLOCK, 1)
            changed = True
        start = text.find(ADAPTIVE_R_INSTALL_START)
        end = text.find(ADAPTIVE_VALIDATION_START)
        if start != -1 and end != -1 and start < end:
            text = text[:start] + ADAPTIVE_R_OFFLINE_CHECK_BLOCK + text[end:]
            changed = True
        return text, changed
    if task_id == "overfull-hbox":
        if OVERFULL_INSTALL_BLOCK in text:
            return text.replace(OVERFULL_INSTALL_BLOCK, OVERFULL_OFFLINE_CHECK_BLOCK, 1), True
        return text, False
    if task_id == "crack-7z-hash":
        changed = False
        for install_block in (CRACK_LZMA_INSTALL_BLOCK, CRACK_LZMA_INSTALL_BLOCK_TRAILING):
            if install_block in text:
                text = text.replace(install_block, CRACK_LZMA_OFFLINE_CHECK_BLOCK, 1)
                changed = True
                break
        if CRACK_7ZIP_INSTALL_LINE in text:
            text = text.replace(CRACK_7ZIP_INSTALL_LINE, CRACK_7ZIP_OFFLINE_CHECK_LINE, 1)
            changed = True
        return text, changed
    if task_id in {"dna-assembly", "dna-insert"}:
        if DNA_INSTALL_BLOCK in text:
            return text.replace(DNA_INSTALL_BLOCK, DNA_OFFLINE_CHECK_BLOCK, 1), True
        return text, False
    if task_id == "financial-document-processor":
        changed = False
        if FINANCIAL_TESSERACT_INSTALL_LINE in text:
            text = text.replace(FINANCIAL_TESSERACT_INSTALL_LINE, FINANCIAL_TESSERACT_OFFLINE_CHECK_LINE, 1)
            changed = True
        if FINANCIAL_UV_RUN_LINE in text:
            text = text.replace(FINANCIAL_UV_RUN_LINE, FINANCIAL_PYTHON_RUN_LINE, 1)
            changed = True
        return text, changed
    if task_id == "custom-memory-heap-crash":
        if CUSTOM_MEMORY_ULIMIT_LINE in text and CUSTOM_MEMORY_ULIMIT_OFFLINE_LINE not in text:
            return text.replace(CUSTOM_MEMORY_ULIMIT_LINE, CUSTOM_MEMORY_ULIMIT_OFFLINE_LINE, 1), True
        return text, False
    if task_id == "sqlite-with-gcov":
        changed = False
        if SQLITE_FOSSIL_INSTALL_BLOCK in text:
            text = text.replace(SQLITE_FOSSIL_INSTALL_BLOCK, SQLITE_FOSSIL_OFFLINE_CHECK_BLOCK, 1)
            changed = True
        if SQLITE_TZDATA_INSTALL_LINE in text:
            text = text.replace(SQLITE_TZDATA_INSTALL_LINE, SQLITE_TZDATA_OFFLINE_CHECK_LINE, 1)
            changed = True
        if SQLITE_BUILD_INSTALL_LINE in text:
            text = text.replace(SQLITE_BUILD_INSTALL_LINE, SQLITE_BUILD_OFFLINE_CHECK_BLOCK, 1)
            changed = True
        return text, changed
    if task_id == "nginx-request-logging":
        changed = False
        if NGINX_INSTALL_LINE in text:
            text = text.replace(NGINX_INSTALL_LINE, NGINX_OFFLINE_CHECK_LINE, 1)
            changed = True
        if NGINX_LOCAL_CURL_LINE in text:
            text = text.replace(NGINX_LOCAL_CURL_LINE, NGINX_LOCAL_STATUS_LINE, 1)
            changed = True
        return text, changed
    if task_id == "configure-git-webserver":
        if CONFIGURE_GIT_WEBSERVER_INSTALL_BLOCK in text:
            return text.replace(
                CONFIGURE_GIT_WEBSERVER_INSTALL_BLOCK,
                CONFIGURE_GIT_WEBSERVER_OFFLINE_CHECK_BLOCK,
                1,
            ), True
        return text, False
    if task_id == "build-pmars":
        start = text.find(PMARS_SETUP_START)
        end = text.find(PMARS_BUILD_START)
        if start != -1 and end != -1 and start < end:
            return text[:start] + PMARS_OFFLINE_CHECK_BLOCK + text[end:], True
        return text, False
    if task_id == "pypi-server":
        changed = False
        if PYPI_APT_INSTALL_BLOCK in text:
            text = text.replace(PYPI_APT_INSTALL_BLOCK, PYPI_APT_OFFLINE_CHECK_BLOCK, 1)
            changed = True
        if PYPI_VENV_INSTALL_BLOCK in text:
            text = text.replace(PYPI_VENV_INSTALL_BLOCK, PYPI_VENV_OFFLINE_CHECK_BLOCK, 1)
            changed = True
        else:
            venv_start = text.find("python3 -m venv /opt/pypiserver/venv")
            venv_install = "/opt/pypiserver/venv/bin/pip install pypiserver==2.3.2 passlib[bcrypt]==1.7.4 bcrypt==4.3.0 packaging==25.0\n"
            venv_end = text.find(venv_install, venv_start if venv_start != -1 else 0)
            if venv_start != -1 and venv_end != -1:
                venv_end += len(venv_install)
                text = text[:venv_start] + PYPI_VENV_OFFLINE_CHECK_BLOCK + text[venv_end:]
                changed = True
        if PYPI_SYSTEM_BUILD_INSTALL_LINE in text:
            text = text.replace(PYPI_SYSTEM_BUILD_INSTALL_LINE, PYPI_BUILD_OFFLINE_CHECK_BLOCK, 1)
            changed = True
        if PYPI_RUNTIME_BUILD_INSTALL_LINE in text:
            text = text.replace(PYPI_RUNTIME_BUILD_INSTALL_LINE, PYPI_BUILD_OFFLINE_CHECK_BLOCK, 1)
            changed = True
        if PYPI_SERVER_VENV_CMD in text:
            text = text.replace(PYPI_SERVER_VENV_CMD, PYPI_SERVER_BAKED_CMD, 1)
            changed = True
        return text, changed
    if task_id == "chess-best-move":
        changed = False
        if CHESS_STOCKFISH_INSTALL_LINE in text:
            text = text.replace(CHESS_STOCKFISH_INSTALL_LINE, CHESS_STOCKFISH_OFFLINE_CHECK_LINE, 1)
            changed = True
        if CHESS_PIP_INSTALL_LINE in text:
            text = text.replace(CHESS_PIP_INSTALL_LINE, CHESS_PYTHON_OFFLINE_CHECK_BLOCK, 1)
            changed = True
        # Earlier repeated repair passes could prefix /usr/bin/ again because
        # "python3 solve.py" is a substring of "/usr/bin/python3 solve.py".
        repaired = []
        for line in text.splitlines(keepends=True):
            if line.strip().endswith("python3 solve.py"):
                newline = "\n" if line.endswith("\n") else ""
                normalized = CHESS_RUN_BAKED_LINE.rstrip("\n") + newline
                if line != normalized:
                    changed = True
                repaired.append(normalized)
            else:
                repaired.append(line)
        text = "".join(repaired)
        return text, changed
    if task_id == "gcode-to-text":
        changed = False
        if GCODE_SETUP_BLOCK in text:
            text = text.replace(GCODE_SETUP_BLOCK, GCODE_OFFLINE_CHECK_BLOCK, 1)
            changed = True
        else:
            start = text.find("apt-get update -y")
            install_line = "apt install -y tesseract-ocr libtesseract-dev"
            end = text.find(install_line, start if start != -1 else 0)
            if start != -1 and end != -1:
                end = text.find("\n", end)
                if end == -1:
                    end = len(text)
                else:
                    end += 1
                text = text[:start] + GCODE_OFFLINE_CHECK_BLOCK + text[end:]
                changed = True
        for before, after in GCODE_RUN_LINES:
            if before != after and before in text:
                text = text.replace(before, after, 1)
                changed = True
        return text, changed
    if task_id == "pytorch-model-cli":
        changed = False
        start = text.find(PYTORCH_MODEL_CLI_PIP_START)
        end = text.find(PYTORCH_MODEL_CLI_WEIGHT_START, start if start != -1 else 0)
        if start != -1 and end != -1 and start < end:
            text = text[:start] + PYTORCH_MODEL_CLI_PYTHON_OFFLINE_CHECK_BLOCK + text[end:]
            changed = True
        start = text.find(PYTORCH_MODEL_CLI_GCC_START)
        end = text.find(PYTORCH_MODEL_CLI_C_FILE_START, start if start != -1 else 0)
        if start != -1 and end != -1 and start < end:
            text = text[:start] + PYTORCH_MODEL_CLI_GCC_OFFLINE_CHECK_BLOCK + text[end:]
            changed = True
        return text, changed
    if task_id == "build-pov-ray":
        changed = False
        start = text.find(POV_RAY_INSTALL_START)
        end = text.find(POV_RAY_CHECK_START, start if start != -1 else 0)
        if start != -1 and end != -1 and start < end:
            text = text[:start] + POV_RAY_OFFLINE_CHECK_BLOCK + text[end:]
            changed = True
        start = text.find(POV_RAY_DOWNLOAD_START)
        end = text.find(POV_RAY_EXTRACT_START, start if start != -1 else 0)
        if start != -1 and end != -1 and start < end:
            text = text[:start] + POV_RAY_COPY_ARCHIVES_BLOCK + text[end:]
            changed = True
        if POV_RAY_WGET_CHECK_LINE in text:
            text = text.replace(POV_RAY_WGET_CHECK_LINE, "", 1)
            changed = True
        return text, changed
    if task_id == "install-windows-3.11":
        changed = False
        start = text.find(INSTALL_WINDOWS_QEMU_SOURCE_START)
        end = text.find(INSTALL_WINDOWS_IMAGE_CHECK_START, start if start != -1 else 0)
        if start != -1 and end != -1 and start < end:
            text = text[:start] + INSTALL_WINDOWS_QEMU_OFFLINE_CHECK_BLOCK + text[end:]
            changed = True
        if "EXTERNAL_IP=$(wget -qO-" in text:
            repaired_lines = []
            for line in text.splitlines(keepends=True):
                if "EXTERNAL_IP=$(wget -qO-" in line:
                    repaired_lines.append(INSTALL_WINDOWS_EXTERNAL_IP_LOCAL_LINE)
                    changed = True
                else:
                    repaired_lines.append(line)
            text = "".join(repaired_lines)
        return text, changed
    if task_id == "mteb-leaderboard":
        if os.environ.get("TB21_ENABLE_MTEB_REPAIR") != "1" and not any(path.is_file() for path in MTEB_LEADERBOARD_READY_SUMMARIES):
            return text, False
        if MTEB_LEADERBOARD_CLONE_BLOCK in text:
            return text.replace(MTEB_LEADERBOARD_CLONE_BLOCK, MTEB_LEADERBOARD_COPY_BLOCK, 1), True
        return text, False
    if task_id == "count-dataset-tokens":
        changed = False
        if COUNT_DATASET_TOKENS_PIP_LINE in text:
            text = text.replace(COUNT_DATASET_TOKENS_PIP_LINE, COUNT_DATASET_TOKENS_OFFLINE_CHECK_BLOCK, 1)
            changed = True
        if COUNT_DATASET_TOKENS_TOKENIZER_LINE in text:
            text = text.replace(COUNT_DATASET_TOKENS_TOKENIZER_LINE, COUNT_DATASET_TOKENS_TOKENIZER_OFFLINE_LINE, 1)
            changed = True
        return text, changed
    if task_id == "make-doom-for-mips":
        if MAKE_DOOM_FOR_MIPS_INSTALL_LINE in text:
            return text.replace(MAKE_DOOM_FOR_MIPS_INSTALL_LINE, MAKE_DOOM_FOR_MIPS_OFFLINE_CHECK_BLOCK, 1), True
        return text, False
    if task_id == "train-fasttext":
        changed = False
        if TRAIN_FASTTEXT_INSTALL_LINE in text:
            text = text.replace(TRAIN_FASTTEXT_INSTALL_LINE, TRAIN_FASTTEXT_OFFLINE_CHECK_LINE, 1)
            changed = True
        if TRAIN_FASTTEXT_GIT_CLONE_LINE in text:
            text = text.replace(TRAIN_FASTTEXT_GIT_CLONE_LINE, TRAIN_FASTTEXT_COPY_BLOCK, 1)
            changed = True
        if TRAIN_FASTTEXT_BUILD_LINE in text:
            text = text.replace(TRAIN_FASTTEXT_BUILD_LINE, TRAIN_FASTTEXT_BUILD_OFFLINE_LINE, 1)
            changed = True
        return text, changed
    if task_id == "protein-assembly":
        changed = False
        if PROTEIN_ASSEMBLY_INSTALL_LINE in text:
            text = text.replace(PROTEIN_ASSEMBLY_INSTALL_LINE, PROTEIN_ASSEMBLY_OFFLINE_CHECK_BLOCK, 1)
            changed = True
        start = text.find(PROTEIN_ASSEMBLY_DISCOVERY_START)
        end = text.find(PROTEIN_ASSEMBLY_GBLOCK_START, start if start != -1 else 0)
        if start != -1 and end != -1 and start < end:
            text = text[:start] + text[end:]
            changed = True
        return text, changed
    if task_id == "rstan-to-pystan":
        changed = False
        start = text.find(RSTAN_PYSTAN_INSTALL_START)
        end = text.find(RSTAN_PYSTAN_SCRIPT_START, start if start != -1 else 0)
        if start != -1 and end != -1 and start < end:
            text = text[:start] + RSTAN_PYSTAN_OFFLINE_CHECK_BLOCK + text[end:]
            changed = True
        if RSTAN_PYSTAN_RUNTIME_PIP_LINE in text:
            text = text.replace(RSTAN_PYSTAN_RUNTIME_PIP_LINE, "", 1)
            changed = True
        return text, changed
    if task_id == "compile-compcert":
        changed = False
        start = text.find(COMPCERT_INSTALL_START)
        end = text.find(COMPCERT_CC_VER_LINE, start if start != -1 else 0)
        if start != -1 and end != -1 and start < end:
            text = text[:start] + COMPCERT_OFFLINE_CHECK_BLOCK + text[end:]
            changed = True
        if COMPCERT_GIT_CLONE_LINE in text:
            text = text.replace(COMPCERT_GIT_CLONE_LINE, COMPCERT_COPY_BLOCK, 1)
            changed = True
        if COMPCERT_MAKE_SERIAL_LINE in text:
            text = text.replace(COMPCERT_MAKE_SERIAL_LINE, COMPCERT_MAKE_PARALLEL_BLOCK, 1)
            changed = True
        return text, changed
    if task_id == "caffe-cifar-10":
        changed = False
        start = text.find(CAFFE_CIFAR_APT_START)
        end = text.find(CAFFE_CIFAR_INSTALL_END, start if start != -1 else 0)
        if start != -1 and end != -1 and start < end:
            text = text[:start] + CAFFE_CIFAR_OFFLINE_CHECK_BLOCK + text[end:]
            changed = True
        if CAFFE_CIFAR_GIT_LINE in text:
            text = text.replace(CAFFE_CIFAR_GIT_LINE, CAFFE_CIFAR_COPY_BLOCK, 1)
            changed = True
        if CAFFE_CIFAR_OPENCV4_INCLUDE_LINE not in text:
            marker = 'echo \"OPENCV_VERSION := 4\" >> Makefile.config\n'
            if marker in text:
                text = text.replace(marker, marker + CAFFE_CIFAR_OPENCV4_INCLUDE_LINE, 1)
                changed = True
        if CAFFE_CIFAR_HDF5_CONFIG_BLOCK not in text:
            marker = 'echo "LIBRARIES += opencv_core opencv_imgproc opencv_highgui opencv_imgcodecs" >> Makefile.config\n'
            if marker in text:
                text = text.replace(marker, marker + CAFFE_CIFAR_HDF5_CONFIG_BLOCK, 1)
                changed = True
        if CAFFE_CIFAR_OPENCV4_HEADER_PATCH_BLOCK not in text:
            marker = "sed -i 's/CV_LOAD_IMAGE_COLOR/cv::IMREAD_COLOR/g' src/caffe/util/io.cpp\n"
            if marker in text:
                text = text.replace(marker, CAFFE_CIFAR_OPENCV4_HEADER_PATCH_BLOCK + marker, 1)
                changed = True
        return text, changed
    if task_id == "sam-cell-seg":
        changed = False
        start = text.find(SAM_CELL_SEG_INSTALL_START)
        end = text.find(SAM_CELL_SEG_SCRIPT_START, start if start != -1 else 0)
        if start != -1 and end != -1 and start < end:
            text = text[:start] + SAM_CELL_SEG_OFFLINE_CHECK_BLOCK + text[end:]
            changed = True
        if SAM_CELL_SEG_CURL_CHECK_LINE in text:
            text = text.replace(SAM_CELL_SEG_CURL_CHECK_LINE, "", 1)
            changed = True
        return text, changed
    if task_id == "build-cython-ext":
        changed = False
        if BUILD_CYTHON_GIT_CLONE_LINE in text:
            text = text.replace(BUILD_CYTHON_GIT_CLONE_LINE, BUILD_CYTHON_COPY_BLOCK, 1)
            changed = True
        if BUILD_CYTHON_PIP_INSTALL_LINE in text:
            text = text.replace(BUILD_CYTHON_PIP_INSTALL_LINE, BUILD_CYTHON_IMPORT_CHECK_BLOCK, 1)
            changed = True
        if BUILD_CYTHON_EDITABLE_INSTALL_LINE in text:
            text = text.replace(BUILD_CYTHON_EDITABLE_INSTALL_LINE, BUILD_CYTHON_PTH_BLOCK, 1)
            changed = True
        return text, changed
    return text, False


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--dataset", type=Path, default=DEFAULT_DATASET)
    parser.add_argument("--expected-tasks", type=int, default=EXPECTED_TASKS)
    parser.add_argument("--backup-json", type=Path, default=None)
    parser.add_argument("--execute", action="store_true")
    args = parser.parse_args()

    dataset = args.dataset
    if not dataset.is_dir():
        raise SystemExit(f"dataset missing: {dataset}")

    run_tests = sorted(dataset.glob("*/run-tests.sh"))
    compose_files = sorted(dataset.glob("*/docker-compose.yaml"))
    solution_files = sorted(dataset.glob("*/solution.sh"))
    test_output_files = sorted(dataset.glob("*/tests/test_outputs.py"))
    if len(run_tests) != args.expected_tasks or len(compose_files) != args.expected_tasks:
        raise SystemExit(
            f"unexpected task count: run_tests={len(run_tests)} compose={len(compose_files)} expected={args.expected_tasks}"
        )

    before_direct, before_direct_samples = count_markers(run_tests, NETWORK_MARKERS)
    before_runtime, before_runtime_samples = count_markers(run_tests, RUNTIME_MARKERS)
    before_public, before_public_samples = count_markers(compose_files, COMPOSE_PUBLIC_MARKERS)
    before_solution_network, before_solution_network_samples = count_markers(solution_files, SOLUTION_NETWORK_MARKERS)
    before_test_outputs_network, before_test_outputs_network_samples = count_markers(test_output_files, TEST_OUTPUT_NETWORK_MARKERS)

    changes: list[dict[str, object]] = []
    planned_run_texts: list[tuple[Path, str]] = []
    planned_compose_texts: list[tuple[Path, str]] = []
    planned_solution_texts: list[tuple[Path, str]] = []
    planned_test_output_texts: list[tuple[Path, str]] = []
    run_tests_changed = 0
    compose_changed = 0
    compose_removed_lines = 0
    solution_changed = 0
    test_outputs_changed = 0

    for path in run_tests:
        before = path.read_text(encoding="utf-8")
        after, changed = repair_run_tests(path, before)
        planned_run_texts.append((path, after))
        if not changed:
            continue
        run_tests_changed += 1
        entry = {
            "path": str(path),
            "kind": "run-tests.sh",
            "before_sha256": sha256(path),
            "after_sha256": hashlib.sha256(after.encode("utf-8")).hexdigest(),
            "action": "replace_runtime_resolver_with_python3_m_pytest",
        }
        changes.append(entry)
        if args.execute:
            path.write_text(after, encoding="utf-8")

    for path in compose_files:
        before = path.read_text(encoding="utf-8")
        after, removed = repair_compose(before)
        planned_compose_texts.append((path, after))
        if removed == 0:
            continue
        compose_changed += 1
        compose_removed_lines += removed
        entry = {
            "path": str(path),
            "kind": "docker-compose.yaml",
            "before_sha256": sha256(path),
            "after_sha256": hashlib.sha256(after.encode("utf-8")).hexdigest(),
            "removed_environment_lines": removed,
            "action": "remove_public_proxy_index_and_resolver_env",
        }
        changes.append(entry)
        if args.execute:
            path.write_text(after, encoding="utf-8")

    for path in solution_files:
        before = path.read_text(encoding="utf-8")
        after, changed = repair_solution(path, before)
        planned_solution_texts.append((path, after))
        if not changed:
            continue
        solution_changed += 1
        entry = {
            "path": str(path),
            "kind": "solution.sh",
            "before_sha256": sha256(path),
            "after_sha256": hashlib.sha256(after.encode("utf-8")).hexdigest(),
            "action": f"repair_{path.parent.name}_solution_runtime_closure",
        }
        changes.append(entry)
        if args.execute:
            path.write_text(after, encoding="utf-8")

    for path in test_output_files:
        before = path.read_text(encoding="utf-8")
        after, changed = repair_test_outputs(path, before)
        planned_test_output_texts.append((path, after))
        if not changed:
            continue
        test_outputs_changed += 1
        entry = {
            "path": str(path),
            "kind": "tests/test_outputs.py",
            "before_sha256": sha256(path),
            "after_sha256": hashlib.sha256(after.encode("utf-8")).hexdigest(),
            "action": f"repair_{path.parent.parent.name}_test_outputs_runtime_closure",
        }
        changes.append(entry)
        if args.execute:
            path.write_text(after, encoding="utf-8")

    after_direct, after_direct_samples = count_markers_in_texts(planned_run_texts, NETWORK_MARKERS)
    after_runtime, after_runtime_samples = count_markers_in_texts(planned_run_texts, RUNTIME_MARKERS)
    after_public, after_public_samples = count_markers_in_texts(planned_compose_texts, COMPOSE_PUBLIC_MARKERS)
    after_solution_network, after_solution_network_samples = count_markers_in_texts(
        planned_solution_texts, SOLUTION_NETWORK_MARKERS
    )
    after_test_outputs_network, after_test_outputs_network_samples = count_markers_in_texts(planned_test_output_texts, TEST_OUTPUT_NETWORK_MARKERS)

    if args.backup_json is None:
        stamp = _dt.datetime.utcnow().strftime("%Y%m%d_%H%M%S")
        backup_json = DEFAULT_BACKUP_DIR / f"tb21_full89_runtime_closure_repair_{stamp}.json"
    else:
        backup_json = args.backup_json
    backup_json.parent.mkdir(parents=True, exist_ok=True)

    report = {
        "schema_version": "agentic_bench.tb21_runtime_closure_repair.v2",
        "generated_at_utc": _dt.datetime.utcnow().isoformat(timespec="seconds") + "Z",
        "dataset": str(dataset),
        "execute": args.execute,
        "expected_tasks": args.expected_tasks,
        "run_tests": len(run_tests),
        "compose_files": len(compose_files),
        "solution_files": len(solution_files),
        "test_output_files": len(test_output_files),
        "run_tests_changed": run_tests_changed,
        "compose_files_changed": compose_changed,
        "compose_removed_lines": compose_removed_lines,
        "solution_files_changed": solution_changed,
        "test_outputs_changed": test_outputs_changed,
        "before_counts": {
            "direct_network_hits": before_direct,
            "runtime_resolver_hits": before_runtime,
            "public_index_or_proxy_hits": before_public,
            "solution_network_hits": before_solution_network,
            "test_outputs_network_hits": before_test_outputs_network,
            "direct_network_samples": before_direct_samples,
            "runtime_resolver_samples": before_runtime_samples,
            "public_index_or_proxy_samples": before_public_samples,
            "solution_network_samples": before_solution_network_samples,
            "test_outputs_network_samples": before_test_outputs_network_samples,
        },
        "after_counts": {
            "direct_network_hits": after_direct,
            "runtime_resolver_hits": after_runtime,
            "public_index_or_proxy_hits": after_public,
            "solution_network_hits": after_solution_network,
            "test_outputs_network_hits": after_test_outputs_network,
            "direct_network_samples": after_direct_samples,
            "runtime_resolver_samples": after_runtime_samples,
            "public_index_or_proxy_samples": after_public_samples,
            "solution_network_samples": after_solution_network_samples,
            "test_outputs_network_samples": after_test_outputs_network_samples,
        },
        "changes": changes,
    }
    backup_json.write_text(json.dumps(report, indent=2, sort_keys=True) + "\n", encoding="utf-8")

    print(f"dataset={dataset}")
    print(f"execute={args.execute}")
    print(
        f"run_tests={len(run_tests)}/{args.expected_tasks} compose={len(compose_files)}/{args.expected_tasks} "
        f"solution={len(solution_files)} test_outputs={len(test_output_files)}"
    )
    print(
        f"run_tests_changed={run_tests_changed} compose_files_changed={compose_changed} "
        f"compose_removed_lines={compose_removed_lines} solution_files_changed={solution_changed} "
        f"test_outputs_changed={test_outputs_changed}"
    )
    print(
        f"before direct={before_direct} runtime={before_runtime} public={before_public} "
        f"solution_network={before_solution_network} test_outputs_network={before_test_outputs_network}"
    )
    print(
        f"after direct={after_direct} runtime={after_runtime} public={after_public} "
        f"solution_network={after_solution_network} test_outputs_network={after_test_outputs_network}"
    )
    print(f"backup_json={backup_json}")
    if not args.execute:
        print("status=dry_run_only")
    else:
        print("status=executed")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
