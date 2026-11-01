function varargout = rdann (recordName, annotator, C, N, N0, type)
  % Same call shape as WFDB-App-Toolbox 0.9.6; sample positions are returned 1-based.
  if (nargin < 3) C = []; endif
  if (nargin < 4) N = []; endif
  if (nargin < 5) N0 = []; endif
  if (nargin < 6) type = []; endif
  command = sprintf ("rdann -r %s -a %s", recordName, annotator);
  if (! isempty (N0) && N0 > 1) command = [command sprintf(" -f s%d", N0 - 1)]; endif
  if (! isempty (N)) command = [command sprintf(" -t s%d", N)]; endif
  if (! isempty (type)) command = [command " -p " type]; endif
  if (! isempty (C)) command = [command sprintf(" -c %d", C - 1)]; endif
  [status, text] = system ([command " 2>/dev/null"]);
  if (status != 0) error ("rdann failed: %s %s", recordName, annotator); endif
  text = regexprep (text, '\[[^\]]*\]', "0");
  rows = regexp (text, '\S+\s+(\d+)\s+(\S+)\s+(-?\d+)\s+(-?\d+)\s+(-?\d+)[^\n]*', "tokens");
  n = numel (rows);
  ann = zeros (n, 1); types = repmat (" ", n, 1); subtype = repmat (" ", n, 1);
  chan = zeros (n, 1); num = zeros (n, 1);
  for k = 1:n
    ann(k) = str2double (rows{k}{1}) + 1;
    types(k) = rows{k}{2}(1);
    subtype(k) = rows{k}{3}(1);
    chan(k) = str2double (rows{k}{4});
    num(k) = str2double (rows{k}{5});
  endfor
  outputs = {ann, types, subtype, chan, num, cell(n, 1)};
  varargout = outputs(1:max (nargout, 1));
endfunction
