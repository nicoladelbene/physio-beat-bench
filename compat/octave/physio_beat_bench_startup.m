function physio_beat_bench_startup ()
  % Host Octave packages live under the real home, which entries cannot see via HOME.
  real_list = getenv ("PHYSIO_BEAT_BENCH_PKG_LIST");
  if (! isempty (real_list))
    pkg ("local_list", real_list);
  endif
  try
    pkg ("load", "signal");
  catch
  end_try_catch
endfunction
