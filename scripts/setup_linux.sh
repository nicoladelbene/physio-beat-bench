#!/bin/bash
# Install the native tools the bench needs on Debian/Ubuntu, and build WFDB 10.7.0 into
# data/tools/wfdb. Tested on GitHub's ubuntu-24.04 runners; other distributions need equivalents.
set -euo pipefail
# octave-dev provides mkoctfile, which some entries use to build MEX files (Homebrew's Octave has it).
# OpenJDK 21 reads Java sources as UTF-8 like the macOS JDK; the runner puts it first on PATH.
sudo apt-get update
sudo apt-get install -y --no-install-recommends \
  build-essential bubblewrap curl ca-certificates perl \
  octave octave-dev octave-control octave-signal octave-statistics octave-image \
  libgsl-dev libboost-dev openjdk-21-jdk-headless flac libflac-dev libsndfile1-dev libcurl4-openssl-dev

# Ubuntu 23.10+ blocks unprivileged user namespaces through AppArmor, which bubblewrap needs.
# CI runners are disposable, so the restriction is lifted there. On your own machine, prefer an
# AppArmor profile for bwrap; the bench refuses to run entries rather than run them unsandboxed.
if [ "${CI:-}" = true ] && [ -e /proc/sys/kernel/apparmor_restrict_unprivileged_userns ]; then
  sudo sysctl -w kernel.apparmor_restrict_unprivileged_userns=0
fi

mkdir -p data/tools
tools=$(cd data/tools && pwd)
if [ ! -x "$tools/wfdb/bin/bxb" ]; then
  curl -fL -o "$tools/wfdb.tar.gz" https://github.com/bemoody/wfdb/archive/refs/tags/10.7.0.tar.gz
  tar -xzf "$tools/wfdb.tar.gz" -C "$tools"
  (cd "$tools/wfdb-10.7.0" && ./configure --prefix="$tools/wfdb" --without-netfiles && make -j"$(nproc)" install)
fi
echo "Now run: export WFDB_HOME=$tools/wfdb"
