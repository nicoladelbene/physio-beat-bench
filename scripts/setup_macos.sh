#!/bin/bash
# Install the native tools the bench needs, and build WFDB 10.7.0 into data/tools/wfdb.
set -euo pipefail
brew install octave gsl boost bash openjdk flac libsndfile curl
packages=$(octave --quiet --eval "x = pkg('list'); printf('%s ', cellfun(@(p) p.name, x, 'UniformOutput', false){:})")
for package in control signal datatypes statistics image; do  # datatypes is required by statistics
  case " $packages " in *" $package "*) ;; *) octave --quiet --eval "pkg install -forge $package" ;; esac
done
mkdir -p data/tools
tools=$(cd data/tools && pwd)
if [ ! -x "$tools/wfdb/bin/bxb" ]; then
  curl -fL -o "$tools/wfdb.tar.gz" https://github.com/bemoody/wfdb/archive/refs/tags/10.7.0.tar.gz
  tar -xzf "$tools/wfdb.tar.gz" -C "$tools"
  (cd "$tools/wfdb-10.7.0" && ./configure --prefix="$tools/wfdb" --without-netfiles && make -j8 install)
fi
echo "Now run: export WFDB_HOME=$tools/wfdb"
