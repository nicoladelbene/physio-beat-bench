function physio_beat_bench_call (name, record, varargin)
  % Pass only the arguments the entry's function declares.
  declared = nargin (name);
  if (declared >= 0)
    varargin = varargin(1:min (numel (varargin), max (declared - 1, 0)));
  endif
  feval (name, record, varargin{:});
endfunction
