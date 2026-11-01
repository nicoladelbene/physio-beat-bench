function wrann (recordName, annotator, ann, annType, subType, chan, num)
  % Same call shape as WFDB-App-Toolbox 0.9.6; input positions are 1-based.
  if (nargin < 4 || isempty (annType)) annType = "N"; endif
  if (nargin < 5 || isempty (subType)) subType = "0"; endif
  if (nargin < 6 || isempty (chan)) chan = 0; endif
  if (nargin < 7 || isempty (num)) num = 0; endif
  if (iscell (annType)) annType = char (annType); endif
  ann = ann(:) - 1; L = numel (ann);
  if (numel (annType) == 1) annType = repmat (annType, L, 1); endif
  if (numel (subType) == 1) subType = repmat (subType, L, 1); endif
  if (numel (chan) == 1) chan = repmat (chan, L, 1); endif
  if (numel (num) == 1) num = repmat (num, L, 1); endif
  file = sprintf ("%s_%s_%d.pbbtmp", recordName, annotator, getpid ());
  handle = fopen (file, "w");
  for k = 1:L
    % wrann skips a fixed 9 columns of time before parsing, so the padding here is required.
    fprintf (handle, "    0:00.000 %d %s %s %d %d\n", ann(k), annType(k), subType(k), chan(k), num(k));
  endfor
  fclose (handle);
  status = system (sprintf ("wrann -r %s -a %s < %s", recordName, annotator, file));
  delete (file);
  if (status != 0) error ("wrann failed: %s %s", recordName, annotator); endif
endfunction
