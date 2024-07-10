
import vapoursynth as vs
core = vs.core
clip = core.ffms2.Source(source="input.mkv")
clip.set_output(0)
