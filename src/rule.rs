use std::path::Path;

use crate::violation::Violation;

pub trait Rule: Send + Sync {
    fn code(&self) -> &'static str;
    fn message(&self) -> &'static str;
    fn check(&self, file_path: &Path, content: &str) -> Vec<Violation>;

    fn test_only(&self) -> bool {
        false
    }
}
