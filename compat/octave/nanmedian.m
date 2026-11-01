function y = nanmedian (x)
  if (isvector (x))
    y = median (x(! isnan (x)));
  else
    y = arrayfun (@(k) median (x(! isnan (x(:,k)), k)), 1:columns (x));
  endif
endfunction
