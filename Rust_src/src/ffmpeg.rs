use crate::heuristics;
use crate::scenes;
use ordered_float::NotNan;
use std::cmp::Ordering;
use std::collections::HashMap;
use std::fs;
use std::fs::File;
use std::io;
use std::io::prelude::*;
use std::process::{Command, Output, Stdio};
// use textwrap::dedent;

#[derive(Debug)]
pub struct InputVideo {
    pub raw_name: String,
    vapoursynth_script: String,
}

impl InputVideo {
    pub fn new(input_filename: &str, vapoursynth_commands: &str) -> InputVideo {
        let vapoursynth_script = format!(
            "import vapoursynth as vs
core = vs.core
clip = core.ffms2.Source(source='{input_filename}')
{vapoursynth_commands}
clip.set_output(0)",
        );

        let mut file = File::create("seeking.vpy").expect("couldn't make vpy file");
        file.write_all(vapoursynth_script.as_bytes())
            .expect("Unable to write data to file");

        InputVideo {
            raw_name: String::from(input_filename),
            vapoursynth_script,
        }
    }

    /// Returns a string for the pipe for the InputVideo
    pub fn pipe_command(
        &self,
        start_frame: Option<u64>,
        end_frame: Option<u64>,
        // ) -> Result<Output, std::io::Error> {
    ) -> Vec<u8> {
        let mut command = Command::new("vspipe");
        command.arg("seeking.vpy").args(["-c", "y4m"]);

        if let Some(frame) = start_frame {
            command.arg("--start").arg(format!("{}", frame));
        }

        if let Some(frame) = end_frame {
            command.arg("--end").arg(format!("{}", frame - 1));
        }

        // .args([start_command, end_command])
        return command
            .arg("-")
            .output()
            .expect("Failed to get output")
            .stdout;
    }
}

#[derive(Debug)]
pub struct Encoding {
    pub input_file: InputVideo,
    pub codec: Codecs,
    pub heuristic: heuristics::Heuristics,
}

impl Encoding {
    // https://stackoverflow.com/questions/49218599/write-to-child-process-stdin-in-rust

    /// this renders the video, then gets a heuristic measurement immediately afterwards
    pub fn render_video(
        &self,
        output_file: String,
        frame_start: Option<u64>,
        frame_end: Option<u64>,
        crf_value: u8,
        // ) -> io::Result<Vec<f64>> {
    ) -> Vec<f64> {
        let input_video_seeking = self.input_file.pipe_command(frame_start, frame_end);

        let mut ffmpeg_command = Command::new("ffmpeg");
        ffmpeg_command
            .stdin(Stdio::piped())
            .stdout(Stdio::piped())
            .stderr(Stdio::null()) // removes output to terminal
            .arg("-i")
            .arg("-")
            .arg("-y")
            .arg("-an");

        // the -crf and output may be dependant on codec (eg svt-av1-psy)
        match self.codec {
            Codecs::SVTAV1 {
                film_grain,
                film_grain_synthesis,
                tune,
            } => ffmpeg_command
                .args(["-crf", &crf_value.to_string()])
                .args(["-c:v", "libsvtav1"])
                .args(["-svtav1-params", &format!("tune={tune}:film-grain={film_grain}:film-grain-denoise={film_grain_synthesis}")])
                .arg(&output_file),
            Codecs::Libx265 => ffmpeg_command
                .args(["-crf", &crf_value.to_string()])
                .args(["-c:v", "libx264"])
                .arg(&output_file),
            Codecs::Libx264 => ffmpeg_command
                .args(["-crf", &crf_value.to_string()])
                .args(["-c:v", "libx265"])
                .arg(&output_file),
        };

        let mut ffmpeg_command = ffmpeg_command.spawn().unwrap();
        let child_stdin = ffmpeg_command.stdin.as_mut().unwrap();
        child_stdin.write_all(&input_video_seeking).unwrap();
        // Close stdin to finish and avoid indefinite blocking
        // drop(child_stdin);

        // output because pipe into standalone encoder
        let _output = ffmpeg_command.wait_with_output().unwrap();
        // println!("output = {:?}", _output);

        return self
            .heuristic
            .get_heuristic_from_video(&self.input_file, &output_file, frame_start, frame_end)
            .expect("Getting heuristic failed");
    }

    /// Finds the optimal CRF value for a target heuristic
    pub fn find_optimal_crf(
        &self,
        output_file: String,
        // codec: Codecs,
        // heuristic: heuristics::Heuristics,
        scene: Option<&scenes::Scenes>,
        target_value: f64,
    ) -> (u8, HashMap<u8, f64>, String) {
        let mut crf_heuristic_cache: HashMap<u8, f64> = HashMap::new();
        let (mut minimum, mut maximum) = self.codec.crf_range();

        let tempfilename = |current_crf| {
            format!("temp-{current_crf}-{output_file}-{:?}.mkv", scene).replace(" ", "_")
        };

        // while crf_heuristic_cache.get(let current_crf = (maximum - minimum) / 2).is_none() {
        loop {
            let current_crf = (maximum + minimum) / 2;
            if crf_heuristic_cache.get(&current_crf).is_some() {
                break;
            }

            let heuristic_throughout = match scene {
                Some(ref scene_inner) => self.render_video(
                    tempfilename(current_crf),
                    Some(scene_inner.frame_start),
                    Some(scene_inner.frame_end),
                    current_crf,
                ),
                None => self.render_video(tempfilename(current_crf), None, None, current_crf),
            };

            let average_heuristic: f64 =
                heuristic_throughout.iter().sum::<f64>() / heuristic_throughout.len() as f64;

            crf_heuristic_cache.insert(current_crf, average_heuristic);
            dbg!(format!("{current_crf} = {average_heuristic}"));

            match average_heuristic.total_cmp(&target_value) {
                Ordering::Less => maximum = current_crf,
                Ordering::Greater => minimum = current_crf,
                Ordering::Equal => break,
            }
        }

        let best_crf = crf_heuristic_cache
            .iter()
            .min_by_key(|x| NotNan::new((target_value - *x.1).abs()).unwrap())
            .expect("There should have been at least one CRF tested");

        for file_crf in crf_heuristic_cache.iter() {
            if *file_crf.0 == *best_crf.0 {
                continue;
            }
            match fs::remove_file(tempfilename(*file_crf.0)) {
                Ok(_) => continue,
                Err(e) => eprintln!("Error deleting file. Error message: {e}"),
            }
        }

        return (
            *best_crf.0,
            crf_heuristic_cache.clone(),
            tempfilename(*best_crf.0),
        );
    }
}

#[derive(Copy, Clone, Debug)]
pub enum Codecs {
    SVTAV1 {
        film_grain: u8,
        film_grain_synthesis: bool,
        tune: i8,
    },
    Libx265,
    Libx264,
    // HevcVideotoolbox,
}

impl Codecs {
    pub fn crf_range(&self) -> (u8, u8) {
        let (minimum, maximum) = match self {
            Codecs::SVTAV1 { .. } => (0, 63),
            Codecs::Libx264 => (0, 51),
            Codecs::Libx265 => (0, 51),
            // Codecs::HevcVideotoolbox => (0, 100),
        };
        return (minimum, maximum);
    }
}

/// Concatenates video files to form final video
pub fn concatenate_videos(videos: Vec<String>, output_file: &str) -> io::Result<()> {
    let video_marks: Vec<String> = videos.iter().map(|x| format!("'{x}'")).collect();
    let file_text = format!("file: \n{}", video_marks.join("\n"));

    let mut file = File::create("\"videolist.txt\"")?;
    file.write_all(file_text.as_bytes())
        .expect("Error in write_all");

    Command::new("ffmepg")
        .args(["-f", "concat"])
        .args(["-safe", "0"])
        .args(["-i", "\"videolist.txt\""])
        .args(["-c", "copy"])
        .arg("-y")
        .arg(output_file)
        .output()?;

    Ok(())
}

// pub struct VideoMetadata {}
// impl VideoMetadata {
//     pub fn get_data() {}
// }

#[cfg(test)]
mod tests {
    use super::*;

    const TEST_VIDEO: &str = "small.mp4";

    #[test]
    fn seeking_with_end_frame() {
        let video = InputVideo::new(TEST_VIDEO, "").pipe_command(None, Some(10));
        assert_ne!(format!("output: {}", String::from_utf8(video).unwrap()), "",);
    }

    #[test]
    fn seeking_entire_duration() {
        let video = InputVideo::new(TEST_VIDEO, "").pipe_command(None, None);
        assert_ne!(format!("output: {}", String::from_utf8(video).unwrap()), "",);
    }

    // #[test]
    // fn testing_forming_InputVideo() {
    //     let vapoursynth_data = "";
    //     let test = InputVideo::new("test_input.mp4", vapoursynth_data);
    //     assert!(
    //         test.vapoursynth_script.contains(vapoursynth_data),
    //         "Doesn't contain the vapoursynth data"
    //     );
    //     assert!(test.vapoursynth_script.contains("test_input.mp4"));
    //     assert_eq!(test.pipe_command(None, None), String::from("vspipe -c y4m"));
    // }
}
