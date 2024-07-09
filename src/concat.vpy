import vapoursynth as vs
core = vs.core
clip0 = core.ffms2.Source(source="TEMP-0.mkv")
clip1 = core.ffms2.Source(source="TEMP-1.mkv")
clip2 = core.ffms2.Source(source="TEMP-2.mkv")
clip3 = core.ffms2.Source(source="TEMP-3.mkv")
total_clip = clip0 + clip1 + clip2 + clip3
total_clip.set_output(0)