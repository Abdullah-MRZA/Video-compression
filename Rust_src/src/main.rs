mod ffmpeg;
mod heuristics;
mod scenes;
use serde::{Deserialize, Serialize};

fn main() {
    let video = ffmpeg::InputVideo::new("small.mp4", "");
    let render_data = ffmpeg::Encoding {
        input_file: video,
        codec: ffmpeg::Codecs::Libx264,
        heuristic: heuristics::Heuristics::VMAF,
    };

    render_data.render_video(String::from("output.mkv"), None, None, 30);
    // let scenes = scenes::Scenes::find_all_scenes(video, 1).expect("Couldn't find all scenes");

    // for scene in scenes {
    //     todo!();
    // }
}

// use std::io::{self, Write};
// use std::process::{Command, Stdio};
//
// fn main() -> io::Result<()> {
//     let mut child = Command::new("cat")
//         .stdin(Stdio::piped())
//         .stdout(Stdio::piped())
//         .spawn()?;
//
//     let child_stdin = child.stdin.as_mut().unwrap();
//     child_stdin.write_all(b"Hello, world!\n")?;
//     // Close stdin to finish and avoid indefinite blocking
//
//     let output = child.wait_with_output()?;
//
//     println!("output = {:?}", output);
//
//     Ok(())
// }

// use std::process::Command;
//
// fn main() {
//     // let list_dir = Command::new("ls");
//
//     let val = Command::new("vspipe")
//         .arg("seeking.vpy")
//         .args(["-c", "y4m"])
//         .arg("-")
//         .output()
//         .expect("ls command failed to start")
//         .stdout;
//
//     println!("{}", String::from_utf8(val).unwrap());
// }
