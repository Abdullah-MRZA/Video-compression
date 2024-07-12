
import vapoursynth as vs
core = vs.core
clip = core.ffms2.Source(source="whole.mp4")
clip.set_output(0)
