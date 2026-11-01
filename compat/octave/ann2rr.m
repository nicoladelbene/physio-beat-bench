function varargout = ann2rr (recordName, annotator, N, N0, varargin)
  % Same call shape as WFDB-App-Toolbox 0.9.6: RR durations and interval starts, in samples.
  command = sprintf ("ann2rr -r %s -a %s -V", recordName, annotator);
  if (nargin > 3 && ! isempty (N0)) command = [command sprintf(" -f s%d", N0 - 1)]; endif
  if (nargin > 2 && ! isempty (N)) command = [command sprintf(" -t s%d", N)]; endif
  [status, text] = system ([command " 2>/dev/null"]);
  if (status != 0) error ("ann2rr failed: %s %s", recordName, annotator); endif
  rows = sscanf (text, "%f");
  tm = rows(1:2:end); rr = rows(2:2:end);
  varargout{1} = rr;
  if (nargout > 1) varargout{2} = tm; endif
endfunction
