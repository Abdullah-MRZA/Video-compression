from vapoursynth import core                     # Get an instance of the core
clip = core.bs.VideoSource(source='input.mp4')
clip = clip[10:100]
clip.set_output()  
