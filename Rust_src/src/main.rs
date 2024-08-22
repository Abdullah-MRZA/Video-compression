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
        .map(|x| render_data.find_optimal_crf(Some(x), 70.0))
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

    // Draw graph of data
    {
        use plotters::prelude::*;

        let root_area = BitMapBackend::new("2.5.png", (1200, 800)).into_drawing_area();
        root_area.fill(&WHITE).unwrap();

        let mut ctx = ChartBuilder::on(&root_area)
            .set_label_area_size(LabelAreaPosition::Left, 40)
            .set_label_area_size(LabelAreaPosition::Bottom, 40)
            .caption("Line Plot Demo", ("sans-serif", 40))
            .build_cartesian_2d(-10..10, 0..100)
            .unwrap();

        ctx.configure_mesh().draw().unwrap();

        ctx.draw_series(LineSeries::new((-10..=10).map(|x| (x, x + x)), &GREEN))
            .unwrap();
    }
}
