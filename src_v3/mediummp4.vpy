
import vapoursynth as vs
core = vs.core
clip = core.ffms2.Source(source="medium.mp4")

clip = core.std.CropAbs(clip, 496, 288, 4, 6)

clip.set_output(0)