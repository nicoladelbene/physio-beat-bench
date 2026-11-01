function gqrs (recordName, N, N0, signal, threshold, outputName, highResolution)
  % Mirrors the argument mapping of WFDB-App-Toolbox 0.9.6, including threshold-1 for -m.
  command = sprintf ("gqrs -r %s", recordName);
  if (nargin > 1 && ! isempty (N)) command = [command sprintf(" -t s%d", N - 1)]; endif
  if (nargin > 3 && ! isempty (signal)) command = [command sprintf(" -s %d", signal - 1)]; endif
  if (nargin > 4 && ! isempty (threshold)) command = [command sprintf(" -m %g", threshold - 1)]; endif
  if (nargin > 5 && ! isempty (outputName)) command = [command " -o " outputName]; endif
  if (nargin > 6 && ! isempty (highResolution) && highResolution) command = [command " -H"]; endif
  if (system (command) != 0) error ("gqrs failed: %s", recordName); endif
endfunction
