function y = nanstd (x, flag, dim)
  if (nargin < 2 || isempty (flag)) flag = 0; endif
  if (nargin < 3)
    dim = find (size (x) != 1, 1);
    if (isempty (dim)) dim = 1; endif
  endif
  if (dim == 2) x = x.'; endif
  y = arrayfun (@(k) std (x(! isnan (x(:,k)), k), flag), 1:columns (x));
  if (dim == 1) y = y(:).'; else y = y(:); endif
endfunction
