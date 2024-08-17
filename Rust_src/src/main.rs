mod ffmpeg;
mod heuristics;
mod scenes;

fn main() {
    let video = ffmpeg::InputVideo::new("small.mp4", "");
    let render_data = ffmpeg::Encoding {
        input_file: video,
        codec: ffmpeg::Codecs::Libx264,
        heuristic: heuristics::Heuristics::VMAF,
    };

    let heuristic = render_data.find_optimal_crf(String::from("output.mkv"), None, 70.0);
    // let heuristic = render_data.render_video(String::from("output.mkv"), None, None, 30);
    println!("{:#?}", heuristic);
    // let scenes = scenes::Scenes::find_all_scenes(video, 1).expect("Couldn't find all scenes");
}
