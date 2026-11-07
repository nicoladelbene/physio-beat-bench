#!/bin/bash
# Record the tool versions a run used, so platform differences can be traced to a cause.
set -uo pipefail
line() { printf '%-10s %s\n' "$1" "$(eval "$2" 2>&1 | head -1)"; }
line os "uname -srm"
case "$(uname -s)" in Darwin) line release "sw_vers -productVersion"; cc=/usr/bin/clang ;; *) line release ". /etc/os-release && echo \$PRETTY_NAME"; cc=/usr/bin/gcc ;; esac
line compiler "$cc --version"
line octave "octave --no-gui --no-window-system --version 2>/dev/null | grep -m1 version"
line packages "octave --quiet --no-gui --eval \"x = pkg('list'); printf('%s ', cellfun(@(p) [p.name '-' p.version], x, 'UniformOutput', false){:})\""
# The runner puts Homebrew's OpenJDK first on macOS; /usr/bin/java there is only a stub.
java=java; [ -x /opt/homebrew/opt/openjdk/bin/java ] && java=/opt/homebrew/opt/openjdk/bin/java
line java "$java -version"
line wfdb "\"\$WFDB_HOME/bin/wfdb-config\" --version"
line python "uv run python --version"
line neurokit2 "uv run python -c 'import neurokit2; print(neurokit2.__version__)' 2>/dev/null || echo 'not installed (no --extra modern)'"
line sandbox "if [ \"\$(uname -s)\" = Darwin ]; then echo sandbox-exec; else bwrap --version; fi"
line commit "git rev-parse --short HEAD"
