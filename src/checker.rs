use std::collections::HashMap;
use std::path::Path;

use pyo3::prelude::*;
use pyo3::Py;

use crate::config::{self, Config};
use crate::discovery;
use crate::noqa;
use crate::rule::Rule;
use crate::rules::all_builtin_rules;
use crate::violation::Violation;

fn run_builtin_rules(
    file_path: &Path,
    content: &str,
    is_test: bool,
    config: &Config,
    builtin_rules: &[Box<dyn Rule>],
    violations: &mut Vec<Violation>,
) {
    for rule in builtin_rules {
        if rule.test_only() && !is_test {
            continue;
        }
        if !config.is_rule_selected(rule.code()) {
            continue;
        }
        if config.is_rule_ignored(rule.code(), file_path) {
            continue;
        }

        violations.extend(rule.check(file_path, content));
    }
}

fn run_python_rules(
    file_path: &Path,
    fp_str: &str,
    content: &str,
    is_test: bool,
    config: &Config,
    python_rules: &[Py<PyAny>],
    violations: &mut Vec<Violation>,
    py: Python<'_>,
) -> PyResult<()> {
    for py_rule in python_rules {
        let code: String = py_rule.getattr(py, "code")?.extract(py)?;
        if !config.is_rule_selected(&code) {
            continue;
        }
        if config.is_rule_ignored(&code, file_path) {
            continue;
        }

        let test_only: bool = py_rule.getattr(py, "test_only")?.extract(py)?;
        if test_only && !is_test {
            continue;
        }

        let result: Py<PyAny> = match py_rule.call_method1(py, "check", (fp_str, content)) {
            Ok(r) => r,
            Err(e) => {
                eprintln!("Warning: plugin rule {} failed on {}: {}", code, fp_str, e);
                continue;
            }
        };

        let py_violations: Vec<Violation> = match result.extract(py) {
            Ok(v) => v,
            Err(e) => {
                eprintln!(
                    "Warning: plugin rule {} returned invalid result for {}: {}",
                    code, fp_str, e
                );
                continue;
            }
        };

        violations.extend(py_violations);
    }
    Ok(())
}

pub fn run_check(
    paths: Vec<String>,
    python_rules: &[Py<PyAny>],
    config_path: Option<String>,
    py: Python<'_>,
) -> PyResult<Vec<Violation>> {
    let project_root = config_path
        .as_deref()
        .map(Path::new)
        .unwrap_or_else(|| Path::new("."));
    let config = config::load_config(project_root);
    let builtin_rules = all_builtin_rules();

    let mut all_violations: Vec<Violation> = Vec::new();
    let mut file_contents: HashMap<String, String> = HashMap::new();

    for path_str in &paths {
        let path = Path::new(path_str);
        let files = discovery::collect_python_files(path, &config);

        for file_path in &files {
            let fp_str = file_path.to_string_lossy().to_string();
            let content = match std::fs::read_to_string(file_path) {
                Ok(c) => c,
                Err(e) => {
                    eprintln!("Warning: could not read {}: {}", fp_str, e);
                    continue;
                }
            };
            let is_test = discovery::is_test_file(file_path);

            run_builtin_rules(
                file_path,
                &content,
                is_test,
                &config,
                &builtin_rules,
                &mut all_violations,
            );

            run_python_rules(
                file_path,
                &fp_str,
                &content,
                is_test,
                &config,
                python_rules,
                &mut all_violations,
                py,
            )?;

            file_contents.insert(fp_str, content);
        }
    }

    all_violations.retain(|v| !noqa::is_suppressed(v, &file_contents));
    Ok(all_violations)
}
