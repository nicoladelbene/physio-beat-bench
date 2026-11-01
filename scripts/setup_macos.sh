#!/bin/bash
# Install the native tools the bench needs, and build WFDB into data/tools/wfdb.
set -euo pipefail
brew install octave gsl boost bash openjdk flac libsndfile curl
octave --quiet --eval "pkg install -forge control; pkg install -forge signal"
mkdir -p data/tools
cd data/tools
if [ ! -d wfdb ]; then
  curl -L -o wfdb.zip https://physionet.org/content/wfdb/get-zip/10.7.0/
  unzip -q wfdb.zip
  source_dir=$(find . -maxdepth 2 -name configure -exec dirname {} \; | head -1)
  (cd "$source_dir" && ./configure --prefix="$PWD/../wfdb" --without-netfiles && make -j8 install)
fi
echo "Now run: export WFDB_HOME=$PWD/wfdb"
