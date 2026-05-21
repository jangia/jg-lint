use std::path::Path;

use tree_sitter::{Node, Parser};

use crate::rule::Rule;
use crate::violation::Violation;

pub struct NoIfsInTests;

fn function_name<'a>(node: Node<'a>, source: &'a [u8]) -> Option<&'a str> {
    node.child_by_field_name("name")
        .and_then(|n| n.utf8_text(source).ok())
}

fn collect_ifs(
    node: Node,
    violations: &mut Vec<Violation>,
    fp_str: &str,
    code: &str,
    message: &str,
) {
    if node.kind() == "if_statement" {
        let pos = node.start_position();
        violations.push(Violation {
            file_path: fp_str.to_string(),
            line: pos.row + 1,
            col: pos.column + 1,
            code: code.to_string(),
            message: message.to_string(),
        });
    }
    let mut cursor = node.walk();
    for child in node.children(&mut cursor) {
        collect_ifs(child, violations, fp_str, code, message);
    }
}

fn visit(
    node: Node,
    source: &[u8],
    violations: &mut Vec<Violation>,
    fp_str: &str,
    code: &str,
    message: &str,
) {
    if node.kind() == "function_definition"
        && function_name(node, source).is_some_and(|n| n.starts_with("test_"))
    {
        if let Some(body) = node.child_by_field_name("body") {
            collect_ifs(body, violations, fp_str, code, message);
        }
        return;
    }
    let mut cursor = node.walk();
    for child in node.children(&mut cursor) {
        visit(child, source, violations, fp_str, code, message);
    }
}

impl Rule for NoIfsInTests {
    fn code(&self) -> &'static str {
        "JG002"
    }

    fn message(&self) -> &'static str {
        "if statements are not allowed in test functions"
    }

    fn check(&self, file_path: &Path, content: &str) -> Vec<Violation> {
        let mut parser = Parser::new();
        if parser
            .set_language(&tree_sitter_python::LANGUAGE.into())
            .is_err()
        {
            return vec![];
        }
        let Some(tree) = parser.parse(content, None) else {
            return vec![];
        };

        let mut violations = Vec::new();
        let fp_str = file_path.to_string_lossy().to_string();
        visit(
            tree.root_node(),
            content.as_bytes(),
            &mut violations,
            &fp_str,
            self.code(),
            self.message(),
        );
        violations
    }
}

#[cfg(test)]
mod tests {
    use super::*;

    fn run(src: &str) -> Vec<Violation> {
        NoIfsInTests.check(Path::new("test_x.py"), src)
    }

    #[test]
    fn flags_if_in_test_function() {
        let v = run("def test_foo():\n    if True:\n        pass\n");
        assert_eq!(v.len(), 1);
        assert_eq!(v[0].line, 2);
    }

    #[test]
    fn flags_if_in_test_method() {
        let v = run("class TestX:\n    def test_foo(self):\n        if True:\n            pass\n");
        assert_eq!(v.len(), 1);
    }

    #[test]
    fn ignores_if_in_non_test_function() {
        assert!(run("def helper():\n    if True:\n        pass\n").is_empty());
    }

    #[test]
    fn ignores_top_level_if() {
        assert!(run("if True:\n    pass\n").is_empty());
    }

    #[test]
    fn flags_nested_if() {
        let v = run("def test_foo():\n    for x in []:\n        if x:\n            pass\n");
        assert_eq!(v.len(), 1);
    }

    #[test]
    fn empty_file() {
        assert!(run("").is_empty());
    }
}
