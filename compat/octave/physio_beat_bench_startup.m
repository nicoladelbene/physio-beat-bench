function physio_beat_bench_startup ()
  % Host Octave packages live under the real home, which entries cannot see via HOME.
  real_list = getenv ("PHYSIO_BEAT_BENCH_PKG_LIST");
  if (! isempty (real_list))
    pkg ("local_list", real_list);
  endif
  for name = {"signal", "statistics", "image"}
    try
      pkg ("load", name{1});
    catch failure
      warning ("physio-beat-bench: could not load Octave package %s: %s", name{1}, failure.message);
    end_try_catch
  endfor
endfunction
