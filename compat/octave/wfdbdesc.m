function [siginfo, Fs] = wfdbdesc (recordName)
  % Parses the native wfdbdesc report into the toolbox's struct array.
  [status, text] = system (sprintf ("wfdbdesc %s", recordName));
  if (status != 0) error ("wfdbdesc failed: %s", recordName); endif
  lines = strsplit (text, "\n");
  frequency = ""; length_time = ""; samples = NaN; start = "[0:00:00.000]";
  siginfo = struct ("LengthSamples", {}, "LengthTime", {}, "RecordName", {}, "RecordIndex", {}, ...
    "Description", {}, "SamplingFrequency", {}, "File", {}, "SignalIndex", {}, "StartTime", {}, ...
    "Group", {}, "AdcResolution", {}, "AdcZero", {}, "Baseline", {}, "CheckSum", {}, ...
    "Format", {}, "Gain", {}, "InitialValue", {});
  sig = 0;
  for k = 1:numel (lines)
    line = strtrim (lines{k});
    tokens = regexp (line, '^Group (\d+), Signal (\d+):', "tokens");
    if (! isempty (tokens))
      sig += 1;
      siginfo(sig).RecordName = recordName;
      siginfo(sig).RecordIndex = 0;
      siginfo(sig).Group = str2double (tokens{1}{1});
      siginfo(sig).SignalIndex = str2double (tokens{1}{2});
      siginfo(sig).SamplingFrequency = frequency;
      siginfo(sig).LengthTime = length_time;
      siginfo(sig).LengthSamples = samples;
      siginfo(sig).StartTime = start;
      continue;
    endif
    colon = index (line, ":");
    if (colon == 0) continue; endif
    key = strtrim (line(1:colon-1)); value = strtrim (line(colon+1:end));
    if (sig == 0)
      switch (key)
        case "Sampling frequency"
          frequency = value;
        case "Length"
          length_time = value;
          tokens = regexp (value, '\((\d+) sample', "tokens");
          if (! isempty (tokens)) samples = str2double (tokens{1}{1}); endif
        case "Starting time"
          start = value;
      endswitch
    else
      switch (key)
        case "File"
          siginfo(sig).File = value;
        case "Description"
          siginfo(sig).Description = value;
        case "Gain"
          siginfo(sig).Gain = value;
        case "Initial value"
          siginfo(sig).InitialValue = str2double (value);
        case "Storage format"
          siginfo(sig).Format = value;
        case "I/O"
          # informational only
        case "ADC resolution"
          siginfo(sig).AdcResolution = value;
        case "ADC zero"
          siginfo(sig).AdcZero = str2double (value);
        case "Baseline"
          siginfo(sig).Baseline = str2double (value);
        case "Checksum"
          siginfo(sig).CheckSum = str2double (value);
      endswitch
    endif
  endfor
  value = sscanf (frequency, "%f");
  Fs = repmat (ifelse_scalar (value), numel (siginfo), 1);
endfunction

function y = ifelse_scalar (value)
  if (isempty (value)) y = NaN; else y = value(1); endif
endfunction
