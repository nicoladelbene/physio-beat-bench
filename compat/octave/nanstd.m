function y = nanstd (x)
  if (isvector (x))
    y = std (x(! isnan (x)));
  else
    y = arrayfun (@(k) std (x(! isnan (x(:,k)), k)), 1:columns (x));
  endif
endfunction
