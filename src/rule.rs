use std::path::Path;

use crate::violation::Violation;

pub trait Rule: Send + Sync {
    fn code(&self) -> &'static str;
    #[allow(dead_code)]
    fn message(&self) -> &'static str;
    fn check(&self, file_path: &Path, content: &str) -> Vec<Violation>;

    fn test_only(&self) -> bool {
        false
    }

    fn allow_noqa(&self) -> bool {
        false
    }
}
