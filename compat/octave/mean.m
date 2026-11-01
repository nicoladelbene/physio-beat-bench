function y = mean (x, varargin)
  % The 2014-era definition: sum over count. Octave 11's mean fails on logical input, which several
  % entries use. Also accepts the dimension and NaN flags that Octave's own library functions pass.
  dim = [];
  omit = false;
  for k = 1:numel (varargin)
    if (ischar (varargin{k}))
      omit = omit || strcmpi (varargin{k}, "omitnan");
    else
      dim = varargin{k};
    endif
  endfor
  if (isempty (dim))
    dim = find (size (x) != 1, 1);
    if (isempty (dim)) dim = 1; endif
  endif
  if (islogical (x)) x = double (x); endif
  if (omit)
    valid = ! isnan (x);
    x(! valid) = 0;
    y = sum (x, dim) ./ sum (valid, dim);
  else
    y = sum (x, dim) / size (x, dim);
  endif
endfunction
