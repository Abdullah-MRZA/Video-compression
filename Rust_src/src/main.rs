mod ffmpeg;
mod heuristics;
mod scenes;

use serde::{Deserialize, Serialize};
use serde_json::from_str;
use std::fs;

fn main() {
    let video = ffmpeg::InputVideo::new("small.mp4", "");
    let render_data = ffmpeg::Encoding {
        input_file: video,
        codec: ffmpeg::Codecs::Libx264,
        heuristic: heuristics::Heuristics::VMAF,
    };

    let heuristic = render_data.render_video(String::from("output.mkv"), None, None, 30);
    // let scenes = scenes::Scenes::find_all_scenes(video, 1).expect("Couldn't find all scenes");
}

// #[derive(Debug, Serialize, Deserialize)]
// struct OverallData {
//     version: String,
//     fps: f64,
//     frames: Vec<FrameData>,
// }
//
// #[derive(Debug, Serialize, Deserialize)]
// struct FrameData {
//     #[serde(rename = "frameNum")]
//     frame_num: u64,
//     metrics: HeuristicData,
// }
//
// #[derive(Debug, Serialize, Deserialize)]
// struct HeuristicData {
//     vmaf: f64,
// }
//
// fn main() {
//     let string = fs::read_to_string("logfile.json").unwrap();
//     let data = from_str::<OverallData>(&string);
//
//     if data.is_ok() {
//         println!("{:#?}", data.as_ref().unwrap());
//
//         let vmaflist = data
//             .unwrap()
//             .frames
//             .iter()
//             .map(|x| x.metrics.vmaf)
//             .collect::<Vec<f64>>();
//
//         println!("{:#?}", vmaflist);
//     } else {
//         println!("{:#?}", data.err());
//     }
// }
