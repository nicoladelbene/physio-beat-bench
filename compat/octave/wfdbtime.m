function varargout = wfdbtime (recordName, samples)
  % Sample index to elapsed-time strings, computed from the record's frequency.
  [~, Fs] = wfdbdesc (recordName);
  out = cell (numel (samples), 1);
  for k = 1:numel (samples)
    seconds = samples(k) / Fs(1);
    out{k} = sprintf ("%d:%06.3f", floor (seconds / 60), mod (seconds, 60));
  endfor
  varargout{1} = out;
endfunction
