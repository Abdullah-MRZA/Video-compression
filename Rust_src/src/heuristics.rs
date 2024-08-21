use crate::ffmpeg::InputVideo;
use serde::{Deserialize, Serialize};
use serde_json::from_str;
use std::io::{self, Write};
use std::process::{Command, Stdio};
use std::{fs, u64};

// #[derive(Debug)]
// pub struct Heuristics {
//     pub heuristic: HeuristicsType,
// }

#[derive(Debug)]
// pub enum HeuristicsType {
pub enum Heuristics {
    VMAF,
    // SSIMULACRA2Cpp,
}

impl Heuristics {
    /// Shows what direction of the score leads to a higher quality
    pub fn improving_direction(&self) -> i8 {
        return match self {
            Self::VMAF => 1,
            // Self::SSIMULACRA2Cpp => 1,
        };
    }

    /// Gets the heuristic per frame from the video
    pub fn get_heuristic_from_video(
        &self,
        source_video: &InputVideo,
        rendered_path: &str,
        source_frame_start: Option<u64>,
        source_frame_end: Option<u64>,
    ) -> io::Result<Vec<f64>> {
        return match self {
            Self::VMAF => {
                let mut command = Command::new("ffmpeg");
                let threads_to_use = 6;
                let subsample = 1; // calculate per X frames
                let log_file = format!(
                    "logfile-{}-{}.json",
                    source_frame_start.unwrap_or_else(|| 0),
                    source_frame_end.unwrap_or_else(|| u64::MAX)
                ); // WARNING: this WILL have issues in multithreaded code

                command
                    .stdin(Stdio::piped())
                    .stderr(Stdio::null())
                    .args(["-i", "-"])
                    .args(["-i", rendered_path])
                    .args(["-lavfi", &format!("[1:v]setpts=PTS-STARTPTS[reference];[0:v]setpts=PTS-STARTPTS[distorted];[distorted][reference]libvmaf=n_threads={threads_to_use}:n_subsample={subsample}:log_fmt=json:log_path={log_file}")])
                    .args(["-f", "null", "-"]);

                let mut ffmpeg_command = command.spawn()?;
                let child_stdin = ffmpeg_command.stdin.as_mut().unwrap();
                child_stdin
                    .write_all(&source_video.pipe_command(source_frame_start, source_frame_end))?;
                let _output = ffmpeg_command.wait_with_output()?;

                // Now read the data from the json file

                #[derive(Debug, Serialize, Deserialize)]
                struct OverallData {
                    version: String,
                    fps: f64,
                    frames: Vec<FrameData>,
                }

                #[derive(Debug, Serialize, Deserialize)]
                struct FrameData {
                    #[serde(rename = "frameNum")]
                    frame_num: u64,
                    metrics: HeuristicData,
                }

                #[derive(Debug, Serialize, Deserialize)]
                struct HeuristicData {
                    vmaf: f64,
                }

                let string = fs::read_to_string(&log_file).expect("Unable to read VMAF-json file");
                let data = from_str::<OverallData>(&string)?;

                let vmaflist = data
                    .frames
                    .iter()
                    .map(|x| x.metrics.vmaf)
                    .collect::<Vec<f64>>();

                if fs::remove_file(&log_file).is_err() {
                    eprintln!("Unable to remove {} for VMAF", &log_file);
                }

                Ok(vmaflist)
            } // Self::SSIMULACRA2Cpp => {
              //     let mut ffmpeg_command = Command::new("ffmpeg");
              //     let mut ssimulacra_command = Command::new("ssimulacra");
              //     todo!()
              // }
        };
    }
}
