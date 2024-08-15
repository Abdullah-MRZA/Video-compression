use crate::heuristics;
use crate::scenes;
use ordered_float::NotNan;
use std::cmp::Ordering;
use std::collections::HashMap;
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
    // pub output_file: String,
    pub codec: Codecs,
    pub heuristic: heuristics::Heuristics,
    // pub scenes: Vec<scenes::Scenes>,
}

impl Encoding {
    // https://stackoverflow.com/questions/49218599/write-to-child-process-stdin-in-rust

    /// this renders the video, then gets a heuristic measurement immediately afterwards
    pub fn render_video(
        &self,
        output_file: String,
        // codec: &Codecs,
        // heuristic: &heuristics::Heuristics,
        // scene: &scenes::Scenes,
        frame_start: Option<u64>,
        frame_end: Option<u64>,
        crf_value: u8,
        // ) -> io::Result<Vec<f64>> {
    ) -> Vec<f64> {
        // self.render_video();
        // return heuristic.get_heuristic_from_video();
        let input_video_seeking = self.input_file.pipe_command(frame_start, frame_end);

        let mut ffmpeg_command = Command::new("ffmpeg");
        // ffmepg_command.stdin(Stdio::piped()).args(["-i", "-"]);
        ffmpeg_command
            .stdin(Stdio::piped())
            .stdout(Stdio::piped())
            .arg("-i")
            .arg("-")
            .arg("-y");

        // the -crf and output may be dependant on codec (eg svt-av1-psy)
        ffmpeg_command.args(match self.codec {
            Codecs::SVTAV1 {
                film_grain,
                film_grain_synthesis,
            } => format!("-crf {crf_value} -svtav1params film_grain={film_grain}:film-grain-denoise={film_grain_synthesis} {output_file}"),
            Codecs::Libx265 => format!("-crf {crf_value} {output_file}"),
            Codecs::Libx264 => format!("-crf {crf_value} {output_file}"),
            // Codecs::HevcVideotoolbox => format!(""),
        }.split_whitespace());

        // let mut handle = ffmpeg_command.spawn().expect("FFMPEG command failed");
        // let handle_stdin = handle.stdin.as_mut().expect("something wrong here...");
        // // let mut child_stdin = handle.stdin.take().expect("something wrong here...");
        // let data = input_video_seeking.stdout;
        // handle_stdin.write_all(&data).expect("Error in write_all");
        // // waiting..
        // handle.wait().expect("wait failed");
        // // drop(child_stdin);

        // let mut ffmpeg_command = Command::new("mpv")
        //     .arg("-")
        //     .stdin(Stdio::piped())
        //     .stdout(Stdio::piped())
        //     .spawn()
        //     .unwrap();

        let mut ffmpeg_command = ffmpeg_command.spawn().unwrap();

        let child_stdin = ffmpeg_command.stdin.as_mut().unwrap();
        // child_stdin.write_all(&input_video_seeking.stdout).unwrap();
        child_stdin.write_all(&input_video_seeking).unwrap();
        // Close stdin to finish and avoid indefinite blocking
        // drop(child_stdin);

        let output = ffmpeg_command.wait_with_output().unwrap();

        println!("output = {:?}", output);

        return self
            .heuristic
            .get_heuristic_from_video(&self.input_file, &output_file)
            .expect("Getting heuristic failed");
    }

    /// Finds the optimal CRF value for a target heuristic
    pub fn find_optimal_crf(
        &self,
        output_file: String,
        // codec: Codecs,
        // heuristic: heuristics::Heuristics,
        scene: scenes::Scenes,
        target_value: f64,
    ) -> (u8, HashMap<u8, f64>, String) {
        let mut crf_heuristic_cache: HashMap<u8, f64> = HashMap::new();
        let (mut minimum, mut maximum) = self.codec.crf_range();

        // while crf_heuristic_cache.get(let current_crf = (maximum - minimum) / 2).is_none() {
        loop {
            let current_crf = (maximum - minimum) / 2;
            if crf_heuristic_cache.get(&current_crf).is_some() {
                break;
            }

            let tempfilename = format!("temp - {current_crf} {output_file}.mkv");
            let heuristic_throughout =
                // self.render_video(tempfilename, &codec, &heuristic, &scene, current_crf);
                self.render_video(tempfilename, Some(scene.frame_start), Some(scene.frame_end), current_crf);

            let average_heuristic: f64 =
                heuristic_throughout.iter().sum::<f64>() / heuristic_throughout.len() as f64;

            crf_heuristic_cache.insert(current_crf, average_heuristic);

            match target_value.total_cmp(&average_heuristic) {
                Ordering::Less => maximum = current_crf,
                Ordering::Greater => minimum = current_crf,
                Ordering::Equal => break,
            }
        }

        let best_crf = crf_heuristic_cache
            .iter()
            .min_by_key(|x| NotNan::new((target_value - (*x.0) as f64).abs()).unwrap())
            .expect("There should have been at least one CRF tested");

        return (
            *best_crf.0,
            crf_heuristic_cache.clone(),
            format!("temp - {} {output_file}.mkv", *best_crf.0),
        );
    }
}
#[derive(Copy, Clone, Debug)]
pub enum Codecs {
    SVTAV1 {
        film_grain: u8,
        film_grain_synthesis: bool,
    },
    Libx265,
    Libx264,
    // HevcVideotoolbox,
}

impl Codecs {
    pub fn crf_range(&self) -> (u8, u8) {
        let (minimum, maximum) = match self {
            Codecs::SVTAV1 { .. } => (0, 60),
            Codecs::Libx264 => (0, 40),
            Codecs::Libx265 => (0, 40),
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
        .args([
            "-f",
            "concat",
            "-safe",
            "0",
            "-i",
            "\"videolist.txt\"",
            "-c",
            "copy",
            "-y",
            output_file,
        ])
        .output()?;

    Ok(())
}

pub struct VideoMetadata {}

impl VideoMetadata {
    pub fn get_data() {}
}

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
