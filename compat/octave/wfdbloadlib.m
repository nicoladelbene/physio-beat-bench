function varargout = wfdbloadlib (varargin)
  % The native WFDB tools are on PATH, so there is no Java library to load.
  config = struct ("WFDB_VERSION", "native", "inOctave", true, "WFDB_CUSTOMLIB", 0, "MATLAB_VERSION", version (), ...
    "WFDB_PATH", ".", "WFDB_CAL", "", "DYLD_LIBRARY_PATH", "", "LD_LIBRARY_PATH", "");
  varargout{1} = true;
  if (nargout > 1) varargout{2} = config; endif
endfunction
