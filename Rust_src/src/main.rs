mod ffmpeg;
mod heuristics;
mod scenes;

use indicatif::{ParallelProgressIterator, ProgressIterator};
use rayon::prelude::*;
use std::{collections::HashMap, fs};

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
        .par_iter()
        .progress()
        .map(|x| render_data.find_optimal_crf(x, 70.0))
        .collect::<Vec<(u8, HashMap<u8, f64>, Vec<(u8, f64)>)>>();

    let final_render_filelist = all_heuristics
        .iter()
        .progress()
        .zip(scenes)
        .enumerate()
        .map(|x| {
            let tempfile = format!("part-{}.mkv", x.0);
            let scene = x.1 .1;
            let crf = x.1 .0 .0;
            render_data.render_video(
                &tempfile,
                Some(scene.frame_start),
                Some(scene.frame_end),
                crf,
            );
            tempfile
        })
        .collect::<Vec<String>>();

    ffmpeg::concatenate_videos(final_render_filelist, "combined_final.mkv")
        .expect("Concatenation of videos failed");

    // let heuristic = render_data.render_video(String::from("output.mkv"), None, None, 30);
    println!("{:#?}", all_heuristics);

    let json_data =
        serde_json::to_string_pretty(&all_heuristics).expect("Could not get json data at the end");
    fs::write("json_data.json", json_data).expect("Unable to write json data to file");

    // let csv_data = all_heuristics.iter().map(|x| x.2.clone());
    // fs::write("data.csv", csv_data);
    let test = all_heuristics
        .iter()
        .map(|x| x.2.clone())
        .flatten()
        .collect::<Vec<_>>();

    write_csv(test, "csv_data.csv");
}

fn write_csv(data: Vec<(u8, f64)>, filename: &str) {
    let mut filedata = String::from("crf, heuristic");

    for current_data in data {
        filedata.push_str(&format!("\n{}, {}", current_data.0, current_data.1));
    }

    fs::write(filename, filedata).expect("unable to write csv file");
}

// // Draw graph of data
// {
//     use plotters::prelude::*;
//
//     let root_area = BitMapBackend::new("2.5.png", (1200, 800)).into_drawing_area();
//     root_area.fill(&WHITE).unwrap();
//
//     let mut ctx = ChartBuilder::on(&root_area)
//         .set_label_area_size(LabelAreaPosition::Left, 40)
//         .set_label_area_size(LabelAreaPosition::Bottom, 40)
//         .caption("Line Plot Demo", ("sans-serif", 40))
//         .build_cartesian_2d(-10..10, 0..100)
//         .unwrap();
//
//     ctx.configure_mesh().draw().unwrap();
//
//     let line_graph_data =
//
//     // ctx.draw_series(LineSeries::new((-10..=10).map(|x| (x, x + x)), &GREEN))
//     ctx.draw_series(LineSeries::new(line_graph_data, &GREEN))
//         .unwrap();
// }
