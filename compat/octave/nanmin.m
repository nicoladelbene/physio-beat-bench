function varargout = nanmin (varargin)
  [varargout{1:max (nargout, 1)}] = min (varargin{:});
endfunction
