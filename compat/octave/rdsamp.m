function varargout = rdsamp (recordName, signalList, N, N0, rawUnits, highRes)
  % Same call shape as WFDB-App-Toolbox 0.9.6, backed by the native WFDB rdsamp.
  if (nargin < 2) signalList = []; endif
  if (nargin < 3) N = []; endif
  if (nargin < 4 || isempty (N0)) N0 = 1; endif
  if (nargin < 5 || isempty (rawUnits)) rawUnits = 0; endif
  if (nargin < 6 || isempty (highRes)) highRes = 0; endif
  command = sprintf ("rdsamp -r %s -f s%d", recordName, N0 - 1);
  if (! rawUnits) command = [command " -Ps"]; endif
  if (! isempty (N)) command = [command sprintf(" -t s%d", N)]; endif
  if (! isempty (signalList))
    command = [command " -s" sprintf(" %d", signalList - 1)];
  endif
  if (highRes) command = [command " -H"]; endif
  file = sprintf ("%s_%d.pbbtmp", recordName, getpid ());
  filter = "| sed -E 's/(^|[[:space:]])-($|[[:space:]])/\\1NaN\\2/g;s/(^|[[:space:]])-($|[[:space:]])/\\1NaN\\2/g'";
  if (system (sprintf ("%s %s > %s", command, filter, file)) != 0)
    error ("rdsamp failed: %s", recordName);
  endif
  data = dlmread (file);
  delete (file);
  varargout{1} = data(:,1);
  varargout{2} = data(:,2:end);
  if (nargout > 2)
    [~, Fs] = wfdbdesc (recordName);
    if (! isempty (signalList)) Fs = Fs(signalList); endif
    varargout{3} = Fs(1);
  endif
endfunction
