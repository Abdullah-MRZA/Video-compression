
import vapoursynth as vs
core = vs.core
clip = core.ffms2.Source(source="small.mp4")

clip = core.std.CropAbs(clip, 160, 96, 4, 2)

clip.set_output(0)