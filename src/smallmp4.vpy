
import vapoursynth as vs
core = vs.core
clip = core.ffms2.Source(source="small.mp4")

clip.set_output(0)