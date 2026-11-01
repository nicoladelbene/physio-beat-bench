function varargout = nanmax (varargin)
  [varargout{1:max (nargout, 1)}] = max (varargin{:});
endfunction
