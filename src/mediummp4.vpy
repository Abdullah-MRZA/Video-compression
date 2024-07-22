
import vapoursynth as vs
core = vs.core
clip = core.ffms2.Source(source="medium.mp4")
clip = clip[::2]
clip.set_output(0)