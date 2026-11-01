function y = mean (x, dim)
  % The 2014-era definition: sum over count. Octave 11's mean fails on logical input, which
  % several entries use, so this keeps their arithmetic exactly as it was written for.
  if (nargin < 2)
    dim = find (size (x) != 1, 1);
    if (isempty (dim)) dim = 1; endif
  endif
  y = sum (double (x), dim) / size (x, dim);
endfunction
