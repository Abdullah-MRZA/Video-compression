use crate::ffmpeg::InputVideo;

// #[derive(Debug)]
// pub struct Heuristics {
//     pub heuristic: HeuristicsType,
// }

#[derive(Debug)]
// pub enum HeuristicsType {
pub enum Heuristics {
    VMAF,
}

impl Heuristics {
    pub fn get_heuristic_from_video(
        &self,
        source_path: &InputVideo,
        rendered_path: &str,
    ) -> Result<Vec<f64>, ()> {
        // todo!()
        Ok(vec![10.0])
    }
}
