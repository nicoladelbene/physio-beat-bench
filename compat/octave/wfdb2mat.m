function varargout = wfdb2mat (recordName, signalList, N, N0)
  command = sprintf ("wfdb2mat -r %s", recordName);
  if (nargin > 1 && ! isempty (signalList))
    command = [command " -s" sprintf(" %d", signalList - 1)];
  endif
  if (nargin > 3 && ! isempty (N0)) command = [command sprintf(" -f s%d", N0 - 1)]; endif
  if (nargin > 2 && ! isempty (N)) command = [command sprintf(" -t s%d", N)]; endif
  [status, text] = system (command);
  if (status != 0) error ("wfdb2mat failed: %s", recordName); endif
  if (nargout > 0) varargout{1} = text; endif
endfunction
