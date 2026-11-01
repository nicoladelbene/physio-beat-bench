function y = nanmean (x, dim)
  if (nargin < 2)
    dim = find (size (x) != 1, 1);
    if (isempty (dim)) dim = 1; endif
  endif
  valid = ! isnan (x);
  x(! valid) = 0;
  y = sum (x, dim) ./ sum (valid, dim);
endfunction
