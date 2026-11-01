function y = nanmedian (x, dim)
  if (nargin < 2)
    dim = find (size (x) != 1, 1);
    if (isempty (dim)) dim = 1; endif
  endif
  if (dim == 2) x = x.'; endif
  y = arrayfun (@(k) median (x(! isnan (x(:,k)), k)), 1:columns (x));
  if (dim == 1) y = y(:).'; else y = y(:); endif
endfunction
