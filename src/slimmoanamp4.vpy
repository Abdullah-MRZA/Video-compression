
import vapoursynth as vs
core = vs.core
clip = core.ffms2.Source(source="slimmoana.mp4")

clip = core.std.CropAbs(clip, 1280, 528, 0, 96)

clip.set_output(0)