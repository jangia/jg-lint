use crate::rule::Rule;

mod no_ifs_in_tests;
mod no_inline_imports;

pub fn all_builtin_rules() -> Vec<Box<dyn Rule>> {
    vec![
        Box::new(no_inline_imports::NoInlineImports),
        Box::new(no_ifs_in_tests::NoIfsInTests),
    ]
}
