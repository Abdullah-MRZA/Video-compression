# Video compression

A test for compressing videos extremely efficiently.


> [!CAUTION]
> NOTE: this is still a **work in progress!!!**: 
> There is still a lot of work left to do, for a fully functional build.
> At the moment, only MacOS and linux is supported, but support for windows is coming soon

## Supported Features

- [x] Target quality (eg VMAF, etc) instead of CRF guessing (partially incomplete)
  - [x] Diskless caching for *videos*
- [x] Video splitting based on scene changes
- [x] Local multithreading of rendering (for concurrent encodes --> makes encoding as fast as possible)
  - [x] (with visual markings for progress)
- [x] Recovery from crashes
  - [x] Caching for not wasting encoding (could be further improved too)
- [x] Powerful scripting support
  - [x] Automatic cropping of black bars

If there is a *feature* you would like to implement, or have any other way you could help, get in touch!

## Possible features

- [ ] Adding video metadata
- [ ] HDR support?
- [ ] Shared rendering between computers?

## Documentation?

This piece of software is constantly adapting and changing. Any documentation I could write would become obsolete on any new commit I make.

This software is mainly a tinkerers tool, and requires in-depth knowledge of video compression, python, and heuristics to even function correctly

In the future, I may make it more-user friendly, but at the moment I am prioritising development. 
