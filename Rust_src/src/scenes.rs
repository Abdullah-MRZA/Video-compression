use crate::ffmpeg;
use std::fs;
use std::process::Command;

#[derive(Debug)]
pub struct Scenes {
    pub frame_start: u64,
    pub frame_end: u64,
    // optimal_crf_for_scene: Option<u8>,
}

impl Scenes {
    pub fn py_scenedetect(
        video: ffmpeg::InputVideo,
        minimum_scene_length: u16,
    ) -> Result<Vec<Scenes>, ()> {
        // let name = match video {
        //     ffmpeg::InputVideo::Raw(name) => name,
        //     ffmpeg::InputVideo::Vapoursynth { raw_name, .. } => raw_name,
        // };

        // f"scenedetect --input '{video_data.raw_input_filename.name}' -m {minimum_length_scene_seconds} detect-adaptive list-scenes",
        let scenedetect_data = Command::new("scenedetect")
            .args([
                "--input",
                &video.raw_name[..],
                "-m",
                &minimum_scene_length.to_string()[..],
                "detect-adaptive",
                "list-scenes",
            ])
            .output()
            .expect("scenedetect command failed to start");

        let contents = fs::read_to_string(format!(
            "{}-Scenes.csv",
            video
                .raw_name
                .rsplit_once(".")
                .expect("Video name should have '.' with extension")
                .0
        ))
        .expect("Couldn't read/find scenedetect csv file");
        // )?;

        // let scene_data: Vec<Vec<f64>> = contents
        //     .lines()
        //     .next()
        //     .unwrap()
        //     .lines()
        //     .map(|x| x.split(','))
        //     .map(|x| (x))
        //     .collect();

        todo!();
    }
}
