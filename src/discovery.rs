use std::path::{Path, PathBuf};

use crate::config::Config;

pub fn collect_python_files(path: &Path, config: &Config) -> Vec<PathBuf> {
    if path.is_file() {
        if path.extension().is_some_and(|ext| ext == "py") {
            return vec![path.to_path_buf()];
        }
        return vec![];
    }

    if !path.is_dir() {
        return vec![];
    }

    let excludes: Vec<glob::Pattern> = config
        .effective_exclude()
        .iter()
        .filter_map(|p| {
            let full = format!("{}/{}", path.display(), p);
            glob::Pattern::new(&full).ok()
        })
        .collect();

    let pattern = format!("{}/**/*.py", path.display());
    glob::glob(&pattern)
        .expect("Invalid glob pattern")
        .filter_map(|entry| entry.ok())
        .filter(|p| {
            let p_str = p.to_string_lossy();
            !excludes.iter().any(|ex| ex.matches(&p_str))
        })
        .collect()
}

pub fn is_test_file(path: &Path) -> bool {
    let file_name = path
        .file_name()
        .map(|f| f.to_string_lossy())
        .unwrap_or_default();

    if file_name.starts_with("test_") || file_name.ends_with("_test.py") {
        return true;
    }

    path.components()
        .any(|c| matches!(c, std::path::Component::Normal(s) if s == "tests"))
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn detects_test_paths() {
        assert!(is_test_file(Path::new("tests/test_foo.py")));
        assert!(is_test_file(Path::new("src/tests/test_bar.py")));
        assert!(is_test_file(Path::new("test_something.py")));
        assert!(is_test_file(Path::new("foo_test.py")));
    }

    #[test]
    fn non_test_paths() {
        assert!(!is_test_file(Path::new("src/foo.py")));
        assert!(!is_test_file(Path::new("main.py")));
    }
}
