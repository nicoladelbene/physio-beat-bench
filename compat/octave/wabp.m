function wabp (recordName, beginTime, stopTime, resample, signal)
  command = sprintf ("wabp -r %s", recordName);
  if (nargin > 1 && ! isempty (beginTime)) command = [command " -f " beginTime]; endif
  if (nargin > 2 && ! isempty (stopTime)) command = [command " -t " stopTime]; endif
  if (nargin > 3 && ! isempty (resample) && resample) command = [command " -R"]; endif
  if (nargin > 4 && ! isempty (signal)) command = [command sprintf(" -s %d", signal - 1)]; endif
  if (system (command) != 0) error ("wabp failed: %s", recordName); endif
endfunction
