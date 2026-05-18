use std::collections::{HashMap, HashSet};
use std::sync::LazyLock;

use regex::Regex;

use crate::violation::Violation;

static NOQA_PATTERN: LazyLock<Regex> = LazyLock::new(|| {
    Regex::new(r"#\s*noqa:\s*([A-Z][A-Z0-9]+(?:\s*,\s*[A-Z][A-Z0-9]+)*)").unwrap()
});

pub fn is_suppressed(
    violation: &Violation,
    file_contents: &HashMap<String, String>,
    noqa_allowed: &HashSet<String>,
) -> bool {
    if !noqa_allowed.contains(&violation.code) {
        return false;
    }
    let Some(content) = file_contents.get(&violation.file_path) else {
        return false;
    };
    let Some(line) = content.lines().nth(violation.line - 1) else {
        return false;
    };
    let Some(caps) = NOQA_PATTERN.captures(line) else {
        return false;
    };
    caps[1].split(',').any(|code| code.trim() == violation.code)
}

#[cfg(test)]
mod tests {
    use super::*;

    fn make_violation(file_path: &str, line: usize, code: &str) -> Violation {
        Violation {
            file_path: file_path.to_string(),
            line,
            col: 1,
            code: code.to_string(),
            message: "test".to_string(),
        }
    }

    fn make_contents(file_path: &str, content: &str) -> HashMap<String, String> {
        let mut map = HashMap::new();
        map.insert(file_path.to_string(), content.to_string());
        map
    }

    fn allowed(codes: &[&str]) -> HashSet<String> {
        codes.iter().map(|s| s.to_string()).collect()
    }

    #[test]
    fn suppresses_matching_code_when_allowed() {
        let v = make_violation("foo.py", 1, "JG001");
        let contents = make_contents("foo.py", "x = print('hello')  # noqa: JG001\n");
        assert!(is_suppressed(&v, &contents, &allowed(&["JG001"])));
    }

    #[test]
    fn does_not_suppress_when_code_not_allowed() {
        let v = make_violation("foo.py", 1, "JG001");
        let contents = make_contents("foo.py", "x = print('hello')  # noqa: JG001\n");
        assert!(!is_suppressed(&v, &contents, &allowed(&[])));
    }

    #[test]
    fn does_not_suppress_different_code() {
        let v = make_violation("foo.py", 1, "JG002");
        let contents = make_contents("foo.py", "x = print('hello')  # noqa: JG001\n");
        assert!(!is_suppressed(&v, &contents, &allowed(&["JG002"])));
    }

    #[test]
    fn supports_multiple_codes() {
        let v1 = make_violation("foo.py", 1, "JG001");
        let v2 = make_violation("foo.py", 1, "JG002");
        let v3 = make_violation("foo.py", 1, "JG003");
        let contents = make_contents("foo.py", "x = something  # noqa: JG001, JG002\n");
        let allow = allowed(&["JG001", "JG002", "JG003"]);
        assert!(is_suppressed(&v1, &contents, &allow));
        assert!(is_suppressed(&v2, &contents, &allow));
        assert!(!is_suppressed(&v3, &contents, &allow));
    }

    #[test]
    fn supports_plugin_prefixes() {
        let v = make_violation("foo.py", 1, "MYPLUGIN001");
        let contents = make_contents("foo.py", "x = something  # noqa: MYPLUGIN001\n");
        assert!(is_suppressed(&v, &contents, &allowed(&["MYPLUGIN001"])));
    }

    #[test]
    fn does_not_suppress_other_lines() {
        let v = make_violation("foo.py", 2, "JG001");
        let contents = make_contents("foo.py", "x = 1  # noqa: JG001\ny = 2\n");
        assert!(!is_suppressed(&v, &contents, &allowed(&["JG001"])));
    }

    #[test]
    fn returns_false_for_missing_file() {
        let v = make_violation("missing.py", 1, "JG001");
        let contents = HashMap::new();
        assert!(!is_suppressed(&v, &contents, &allowed(&["JG001"])));
    }

    #[test]
    fn returns_false_for_line_out_of_range() {
        let v = make_violation("foo.py", 99, "JG001");
        let contents = make_contents("foo.py", "x = 1\n");
        assert!(!is_suppressed(&v, &contents, &allowed(&["JG001"])));
    }

    #[test]
    fn handles_extra_spacing() {
        let v = make_violation("foo.py", 1, "JG001");
        let contents = make_contents("foo.py", "x = 1  #  noqa:  JG001\n");
        assert!(is_suppressed(&v, &contents, &allowed(&["JG001"])));
    }
}
