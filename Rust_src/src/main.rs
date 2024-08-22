mod ffmpeg;
mod heuristics;
mod scenes;

use std::collections::HashMap;

fn main() {
    let video = ffmpeg::InputVideo::new("small.mp4", "");
    let scenes = scenes::Scenes::py_scenedetect(&video, 1);

    let render_data = ffmpeg::Encoding {
        input_file: video,
        codec: ffmpeg::Codecs::Libx264,
        heuristic: heuristics::Heuristics::VMAF,
    };

    // let heuristic = render_data.find_optimal_crf(String::from("output test.mkv"), None, 70.0);
    let all_heuristics = scenes
        .iter()
        .map(|x| render_data.find_optimal_crf(String::from("output test.mkv"), Some(x), 70.0))
        .collect::<Vec<(u8, HashMap<u8, f64>, String)>>();

    ffmpeg::concatenate_videos(
        all_heuristics
            .iter()
            .map(|x| x.2.clone())
            .collect::<Vec<String>>(),
        "combined_final.mkv",
    )
    .expect("Concatenation of videos failed");

    // let heuristic = render_data.render_video(String::from("output.mkv"), None, None, 30);
    println!("{:#?}", all_heuristics);
}
