use crate::heuristics;
use crate::scenes;
use ordered_float::NotNan;
use std::cmp::min;
use std::cmp::Ordering;
use std::collections::HashMap;
use std::fs;
use std::fs::File;
use std::io;
use std::io::prelude::*;
use std::process::{Command, Output, Stdio};

#[derive(Debug, Clone)]
pub struct InputVideo {
    pub raw_name: String,
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
        output_file: &str,
        frame_start: Option<u64>,
        frame_end: Option<u64>,
        crf_value: u8,
        // ) -> io::Result<Vec<f64>> {
    ) -> Vec<f64> {
        let input_video_seeking = self.input_file.pipe_command(frame_start, frame_end);

        {
            let crf_range = self.codec.crf_range();
            assert!(crf_range.0 <= crf_value && crf_value <= crf_range.1);
        }

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
                preset,
                film_grain,
                film_grain_synthesis,
                tune,
            } => ffmpeg_command
                .args(["-crf", &crf_value.to_string()])
                .args(["-c:v", "libsvtav1"])
                .args(["-preset", &preset.to_string()])
                .args(["-svtav1-params", &format!("tune={tune}:film-grain={film_grain}:film-grain-denoise={film_grain_synthesis}")])
                .arg(&output_file),
            Codecs::Libx264 => ffmpeg_command
                .args(["-crf", &crf_value.to_string()])
                .args(["-c:v", "libx264"])
                .arg(&output_file),
            Codecs::Libx265 => ffmpeg_command
                .args(["-crf", &crf_value.to_string()])
                .args(["-c:v", "libx265"])
                .arg(&output_file),
            Codecs::SVTAV1PSY {..} => ffmpeg_command
                .args(["-f", "yuv4mpegpipe"])
                .arg("-")
        };

        let mut ffmpeg_command = ffmpeg_command.spawn().unwrap();
        let child_stdin = ffmpeg_command.stdin.as_mut().unwrap();
        child_stdin.write_all(&input_video_seeking).unwrap();
        // Close stdin to finish and avoid indefinite blocking
        // drop(child_stdin);

        // output because pipe into standalone encoder
        let output_ffmpeg = ffmpeg_command.wait_with_output().unwrap();
        // println!("output = {:?}", _output);

        match self.codec {
            Codecs::SVTAV1PSY {
                preset,
                tune,
                film_grain,
                // enable_adaptive_film_grain,
            } => {
                let mut svtav1psy_command = Command::new("SvtAv1EncApp");

                svtav1psy_command
                    .stdin(Stdio::piped())
                    .stdout(Stdio::piped())
                    .stderr(Stdio::null())
                    .args(["-i", "stdin"])
                    .args(["--keyint", "240"])
                    .args(["--preset", &preset.to_string()])
                    .args(["--crf", &crf_value.to_string()])
                    .args(["--tune", &tune.to_string()])
                    .args(["--film-grain", &film_grain.to_string()])
                    // .args([
                    //     "--adaptive-film-grain",
                    //     if enable_adaptive_film_grain { "1" } else { "0" },
                    // ])
                    .args(["-b", &output_file]);

                let mut svtav1psy_command_spawn = svtav1psy_command.spawn().unwrap();
                let child_stdin = svtav1psy_command_spawn.stdin.as_mut().unwrap();
                child_stdin.write_all(&output_ffmpeg.stdout).unwrap();

                let _output = svtav1psy_command_spawn.wait_with_output().unwrap();
            }
            _ => {}
        }

        return self.heuristic.get_heuristic_from_video(
            self.input_file.clone(),
            &output_file,
            frame_start,
            frame_end,
        );
    }

    /// Finds the optimal CRF value for a target heuristic
    /// Does not render the video itself, uses frames (test)
    pub fn find_optimal_crf(
        &self,
        scene: &scenes::Scenes,
        target_value: f64,
    ) -> (u8, HashMap<u8, f64>, Vec<(u8, f64)>) {
        let mut crf_heuristic_cache: HashMap<u8, f64> = HashMap::new();
        let mut crf_heuristic_cache_order_store: Vec<(u8, f64)> = vec![];
        let (mut minimum, mut maximum) = self.codec.crf_range();

        let tempfilename = |current_crf| {
            format!("temp-{current_crf}-{:?}.mkv", scene)
                .replace(" ", "_")
                .replace("\"", "_")
        };

        loop {
            let current_crf = (maximum + minimum) / 2;
            if crf_heuristic_cache.get(&current_crf).is_some() {
                break;
            }

            let heuristic_throughout = self.render_video(
                &tempfilename(current_crf),
                Some(scene.frame_start),
                Some(min(scene.frame_end, scene.frame_start + 2)), // TODO: temporary
                current_crf,
            );

            let average_heuristic: f64 =
                heuristic_throughout.iter().sum::<f64>() / heuristic_throughout.len() as f64;

            crf_heuristic_cache.insert(current_crf, average_heuristic);
            crf_heuristic_cache_order_store.push((current_crf, average_heuristic));
            // dbg!(format!("{current_crf} = {average_heuristic}"));

            // TODO: Add direction of movement
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
            crf_heuristic_cache_order_store.clone(),
        );
    }
}

#[derive(Copy, Clone, Debug)]
pub enum Codecs {
    SVTAV1 {
        film_grain: u8,
        film_grain_synthesis: bool,
        tune: i8,
        preset: u8,
    },
    Libx265,
    Libx264,
    SVTAV1PSY {
        preset: i8,
        tune: u8,
        film_grain: u8,
        // enable_adaptive_film_grain: bool,
    },
    // HevcVideotoolbox,
}

impl Codecs {
    pub fn crf_range(&self) -> (u8, u8) {
        let (minimum, maximum) = match self {
            Codecs::SVTAV1 { .. } => (0, 63),
            Codecs::SVTAV1PSY { .. } => (0, 70),
            Codecs::Libx264 => (0, 51),
            Codecs::Libx265 => (0, 51),
            // Codecs::HevcVideotoolbox => (0, 100),
        };
        return (minimum, maximum);
    }
}

/// Concatenates video files to form final video
pub fn concatenate_videos(videos: Vec<String>, output_file: &str) -> io::Result<()> {
    let video_marks: Vec<String> = videos.iter().map(|x| format!("file '{x}'")).collect();
    let file_text = format!("\n{}", video_marks.join("\n"));

    let mut file = File::create("videolist.txt")?;
    file.write_all(file_text.as_bytes())
        .expect("Error in write_all");

    Command::new("ffmpeg")
        .args(["-f", "concat"])
        .args(["-safe", "0"])
        .args(["-i", "videolist.txt"])
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
