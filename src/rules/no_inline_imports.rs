use std::path::Path;

use tree_sitter::{Node, Parser};

use crate::rule::Rule;
use crate::violation::Violation;

pub struct NoInlineImports;

const IMPORT_KINDS: &[&str] = &[
    "import_statement",
    "import_from_statement",
    "future_import_statement",
];

fn walk<'a>(node: Node<'a>, callback: &mut impl FnMut(Node<'a>)) {
    callback(node);
    let mut cursor = node.walk();
    for child in node.children(&mut cursor) {
        walk(child, callback);
    }
}

impl Rule for NoInlineImports {
    fn code(&self) -> &'static str {
        "JG001"
    }

    fn message(&self) -> &'static str {
        "Imports must be at module top level"
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

        walk(tree.root_node(), &mut |node| {
            if !IMPORT_KINDS.contains(&node.kind()) {
                return;
            }
            let Some(parent) = node.parent() else {
                return;
            };
            if parent.kind() == "module" {
                return;
            }
            let pos = node.start_position();
            violations.push(Violation {
                file_path: fp_str.clone(),
                line: pos.row + 1,
                col: pos.column + 1,
                code: self.code().to_string(),
                message: self.message().to_string(),
            });
        });

        violations
    }
}

#[cfg(test)]
mod tests {
    use super::*;

    fn run(src: &str) -> Vec<Violation> {
        NoInlineImports.check(Path::new("test.py"), src)
    }

    #[test]
    fn allows_top_level_imports() {
        assert!(run("import os\nfrom sys import path\n").is_empty());
    }

    #[test]
    fn flags_import_inside_function() {
        let v = run("def f():\n    import os\n");
        assert_eq!(v.len(), 1);
        assert_eq!(v[0].line, 2);
    }

    #[test]
    fn flags_from_import_inside_method() {
        let v = run("class C:\n    def m(self):\n        from sys import path\n");
        assert_eq!(v.len(), 1);
        assert_eq!(v[0].line, 3);
    }

    #[test]
    fn flags_import_inside_if_block() {
        let v = run("if True:\n    import os\n");
        assert_eq!(v.len(), 1);
    }

    #[test]
    fn empty_file() {
        assert!(run("").is_empty());
    }
}
