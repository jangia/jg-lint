use tree_sitter::{Parser, Tree};

pub fn parse(content: &str) -> Option<Tree> {
    let mut parser = Parser::new();
    let language = tree_sitter_python::LANGUAGE;
    parser.set_language(&language.into()).ok()?;
    parser.parse(content, None)
}
